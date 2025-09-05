from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from prompt_manager import load_prompts
from prompt_templates import get_general_prompt, get_instructed_prompt
from llm_factory import get_llm


def build_prompt(mode: str, text: str) -> str:
    if mode == "general":
        return get_general_prompt(text)
    elif mode == "instructed":
        return get_instructed_prompt(text)
    raise ValueError(f"Unknown mode: {mode}")


def run(args: argparse.Namespace) -> None:
    prompts = load_prompts(
        args.prompt_file,
        text_col=args.prompt_column,
        id_col=args.id_column,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    suffix = f"_{args.out_suffix}" if args.out_suffix else ""
    outfile = outdir / f"{args.mode}{suffix}.jsonl"

    llm = get_llm(
        args.provider,
        args.model,
        temperature=args.temperature,
        num_predict=args.num_predict,
    )

    seen: set[str] = set()
    if args.overwrite and outfile.exists():
        backup = outfile.with_suffix(outfile.suffix + ".bak")
        backup.write_text(outfile.read_text(encoding="utf-8"), encoding="utf-8")
        outfile.write_text("", encoding="utf-8")

    if (not args.force) and outfile.exists():
        for s in outfile.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            s = s.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
                if "id" in rec:
                    seen.add(str(rec["id"]))
            except Exception:
                pass

    n_ok, n_err, n_skip = 0, 0, 0

    with outfile.open("a", encoding="utf-8") as f:
        for item in prompts:
            if (not args.force) and (str(item.id) in seen):
                n_skip += 1
                continue

            prompt = build_prompt(args.mode, item.text)

            t0 = time.perf_counter()
            out_text = ""
            err_msg = None
            try:
                out_text = llm.generate(prompt)
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
            finally:
                dt_ms = int((time.perf_counter() - t0) * 1000)

            created_at = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )

            rec = {
                "id": item.id,
                "mode": args.mode,
                "model": args.model,
                "provider": args.provider,

                "input": item.text,
                "output": out_text if out_text is not None else "",

                "timing": {"latency_ms": dt_ms},
                "created_at": created_at,

                "prompt": prompt,
                "decoding": {
                    "temperature": args.temperature,
                    "num_predict": args.num_predict,
                },
                "efficiency": {"cost_usd": 0.0},
                "len_in_chars": len(item.text or ""),
                "len_prompt_chars": len(prompt or ""),
                "len_out_chars": len(out_text or ""),
            }

            if err_msg:
                rec["error"] = err_msg
                n_err += 1
            else:
                n_ok += 1

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(
        f"[OK] wrote outputs to {outfile.resolve()} "
        f"(ok={n_ok}, err={n_err}, skipped={n_skip})"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt-file", required=True, help="CSV file with prompts")
    p.add_argument("--prompt-column", default="input", help="column name for input text")
    p.add_argument("--id-column", default="id", help="column name for unique id")
    p.add_argument("--mode", choices=["general", "instructed"], required=True)
    p.add_argument("--outdir", default="results/raw")
    p.add_argument("--provider", choices=["openai", "ollama"], default="ollama")
    p.add_argument("--model", default="gemma:7b")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--num-predict", type=int, default=None, dest="num_predict")

    p.add_argument("--overwrite", action="store_true",
                   help="기존 outfile가 있으면 .bak 백업 후 비우고 처음부터 다시 생성")
    p.add_argument("--force", action="store_true",
                   help="기존 outfile의 중복 검사(seen)를 무시하고 모두 생성(중복 라인 생김 주의)")
    p.add_argument("--out-suffix", default="",
                   help="결과 파일명에 접미사 추가 (예: general_<suffix>.jsonl)")
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
