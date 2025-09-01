from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"

DEFAULTS = {
    "general": {"model": "gemma:7b", "mode": "general", "provider": "ollama"},
    "instructed": {
        "model": "gemma:7b-instruct",
        "mode": "instructed",
        "provider": "ollama",
    },
}


def infer_kind(filename: str) -> str:
    name = filename.lower()
    return "instructed" if "instruct" in name else "general"


def hydrate_file(fp: Path):
    kind = infer_kind(fp.name)
    defaults = DEFAULTS[kind]
    src = fp.read_text(encoding="utf-8")
    out_lines = []
    changed = 0
    for ln in src.splitlines():
        s = ln.strip()
        if not s:
            continue
        try:
            rec = json.loads(s)
        except Exception:
            out_lines.append(ln)
            continue
        rec.setdefault("mode", defaults["mode"])
        rec.setdefault("provider", defaults["provider"])
        rec.setdefault("model", defaults["model"])
        rec.setdefault("cost_usd", 0.0)
        out_lines.append(json.dumps(rec, ensure_ascii=False))
        changed += 1
    bak = fp.with_suffix(fp.suffix + ".bak")
    bak.write_text(src, encoding="utf-8")
    fp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"[OK] hydrated {fp.name} (records={changed}) -> backup: {bak.name}")


def main():
    files = sorted(RAW.glob("*.jsonl"))
    if not files:
        print("[WARN] no files in results/raw")
        return
    for fp in files:
        hydrate_file(fp)


if __name__ == "__main__":
    main()
