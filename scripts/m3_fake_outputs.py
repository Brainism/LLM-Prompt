from __future__ import annotations
from pathlib import Path
import json, random

def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def main():
    refs = {d["id"]: d["reference"] for d in load_jsonl(Path("data/raw/references/references.jsonl"))}
    man  = {m["id"]: m for m in json.loads(Path("data/manifest/split_manifest_main.json").read_text(encoding="utf-8"))}
    out = []
    for id_, ref in refs.items():
        if id_ not in man: continue
        toks = ref.split()
        random.shuffle(toks)
        pred = " ".join(toks[: max(3, int(0.9*len(toks)))])
        out.append({
            "id": id_,
            "output": pred,
            "latency_ms": random.randint(200, 1800),
            "prompt_tokens": random.randint(50, 200),
            "completion_tokens": random.randint(20, 120),
            "model_id": "fake-model",
            "prompt_id": "baseline"
        })
    Path("results/raw").mkdir(parents=True, exist_ok=True)
    with open("results/raw/fake_outputs.jsonl", "w", encoding="utf-8") as f:
        for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[fake] wrote results/raw/fake_outputs.jsonl ({len(out)} items)")

if __name__ == "__main__":
    main()