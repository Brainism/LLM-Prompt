from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from compliance_rules import evaluate_item, parse_params
from llm_factory import get_llm
from prompt_manager import load_prompts
from prompt_templates import get_general_prompt, get_instructed_prompt


def build_prompt(mode: str, text: str) -> str:
    if mode == "general":
        return get_general_prompt(text)
    if mode == "instructed":
        return get_instructed_prompt(text)
    raise ValueError(f"Unknown mode: {mode}")


def stricter_suffix() -> str:
    return (
        "\n\n[?ъ떆?? ??洹쒖튃??紐⑤몢 吏?ㅺ퀬 寃곌낵留?異쒕젰?섎씪. "
        "癒몃━留??ㅻ챸/異붽? 臾몄옣/肄붾뱶釉붾줉/諛깊떛 湲덉?."
    )


def load_meta(csv_path: str) -> dict[str, dict]:
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    meta = {}
    for _, r in df.iterrows():
        meta[str(r["prompt_id"])] = {
            "scenario": str(r.get("scenario", "")),
            "param": str(r.get("param", "")),
        }
    return meta


def run(args: argparse.Namespace) -> None:
    prompts = load_prompts(
        args.prompt_file, text_col=args.prompt_column, id_col=args.id_column
    )
    meta = load_meta(args.prompt_file)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    llm = get_llm(
        args.provider,
        args.model,
        temperature=args.temperature,
        num_predict=args.num_predict,
    )
    llm_retry = (
        get_llm(
            args.provider,
            args.model,
            temperature=args.retry_temperature,
            num_predict=args.num_predict,
        )
        if args.retry > 0
        else None
    )

    for item in prompts:
        prompt = build_prompt(args.mode, item.text)
        out_text = llm.generate(prompt)

        info = meta.get(item.id, {"scenario": "", "param": ""})
        params = parse_params(info.get("param", ""))
        passed, reason = (
            evaluate_item(info.get("scenario", ""), out_text, params)
            if info.get("scenario")
            else (True, "skip")
        )

        attempts = 1
        final_text, final_passed, final_reason = out_text, passed, reason

        if not passed and args.retry > 0 and llm_retry is not None:
            attempts = 2
            retry_prompt = prompt + stricter_suffix()
            retry_text = llm_retry.generate(retry_prompt)
            r_ok, r_reason = evaluate_item(info.get("scenario", ""), retry_text, params)
            if r_ok:
                final_text, final_passed, final_reason = retry_text, r_ok, r_reason
            else:
                final_text, final_passed, final_reason = retry_text, r_ok, r_reason

        payload = {
            "id": item.id,
            "prompt_type": args.mode,
            "output_text": final_text,
            "compliance_passed": bool(final_passed),
            "compliance_reason": final_reason,
            "attempts": attempts,
        }
        (outdir / f"{item.id}_{args.mode}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"[OK] wrote outputs (retry={args.retry}) -> {outdir.resolve()}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--prompt-column", default="text")
    p.add_argument("--id-column", default="prompt_id")
    p.add_argument("--mode", choices=["general", "instructed"], required=True)
    p.add_argument("--outdir", default="results/batch_outputs")
    p.add_argument("--provider", choices=["openai", "ollama"], default="ollama")
    p.add_argument("--model", default="gemma:7b")
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--num-predict", type=int, default=None, dest="num_predict")
    p.add_argument("--retry", type=int, default=1)
    p.add_argument(
        "--retry-temperature", type=float, default=0.0, dest="retry_temperature"
    )
    return p.parse_args()


if __name__ == "__main__":
    run(parse_args())
