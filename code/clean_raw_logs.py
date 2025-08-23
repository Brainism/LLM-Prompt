import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"

def load_jsonl(fp: Path):
    for ln in fp.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except:
            continue

def write_jsonl(fp: Path, records):
    fp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")

def dedupe(fp: Path):
    recs = list(load_jsonl(fp))
    last = {}
    for r in recs:
        mode = r.get("mode") or ("instructed" if "instruct" in fp.name.lower() else "general")
        rid = r.get("id") or r.get("item_id") or r.get("example_id")
        if rid is None:
            continue
        last[(mode, rid)] = r

    deduped = list(last.values())
    bak = fp.with_suffix(fp.suffix + ".bak")
    bak.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
    write_jsonl(fp, deduped)
    print(f"[OK] {fp.name}: {len(recs)} -> {len(deduped)} (backup: {bak.name})")

def main():
    files = sorted(RAW.glob("*.jsonl"))
    if not files:
        print("[WARN] no jsonl in results/raw")
        return
    for fp in files:
        dedupe(fp)

if __name__ == "__main__":
    main()