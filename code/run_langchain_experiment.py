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
    outfile = outdir / f"{args.mode}.jsonl"
    llm = get_llm(
        args.provider,
        args.model,
        temperature=args.temperature,
        num_predict=args.num_predict,
    )

    n_ok, n_err = 0, 0
    with outfile.open("w", encoding="utf-8") as f:
        for item in prompts:
            prompt = build_prompt(args.mode, item.text)
            t0 = time.perf_counter()
            out_text = ""
            err_msg = None

            try:
                out_text = llm.generate(prompt)
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
            finally:
                dt_ms = (time.perf_counter() - t0) * 1000.0

            ts_utc = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

            rec = {
                "id": item.id,
                "input": item.text,
                "prompt": prompt, 
                "output": out_text if out_text is not None else "",
                "latency_ms": float(dt_ms),
                "mode": args.mode,
                "provider": args.provider,
                "model": args.model,
                "cost_usd": 0.0,
                "temperature": args.temperature,
                "num_predict": args.num_predict,
                "timestamp": ts_utc,
                "len_in": len(prompt),
                "len_out": len(out_text or ""),
            }
            if err_msg:
                rec["error"] = err_msg
                n_err += 1
            else:
                n_ok += 1

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[OK] wrote outputs to {outfile.resolve()} (ok={n_ok}, err={n_err})")


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
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())