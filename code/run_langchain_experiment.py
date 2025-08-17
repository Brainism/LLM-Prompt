from __future__ import annotations
import argparse, json
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
    prompts = load_prompts(args.prompt_file, text_col=args.prompt_column, id_col=args.id_column)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    llm = get_llm(args.provider, args.model, temperature=args.temperature, num_predict=args.num_predict)

    for item in prompts:
        prompt = build_prompt(args.mode, item.text)
        out_text = llm.generate(prompt)
        payload = {"id": item.id, "prompt_type": args.mode, "output_text": out_text}
        (outdir / f"{item.id}_{args.mode}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"[OK] wrote outputs to {outdir.resolve()}")

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
    return p.parse_args()

if __name__ == "__main__":
    run(parse_args())