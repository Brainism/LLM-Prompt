import csv, json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
RAWDIR = ROOT / "results" / "raw"

def parse_ts(s: str) -> float:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0

def read_id_set(csv_path: Path, id_col: str) -> list[str]:
    ids = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ids.append(str(row[id_col]))
    return ids

def load_jsonl(fp: Path):
    if not fp.exists():
        return []
    out = []
    for ln in fp.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out

def write_jsonl(fp: Path, recs):
    fp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")

def canonize_one(mode: str, records: list[dict], allowed_ids: set[str]) -> list[dict]:
    latest = {}
    kept, dropped = 0, 0
    for r in records:
        rid = str(r.get("id") or r.get("item_id") or r.get("example_id") or "")
        if not rid:
            dropped += 1
            continue
        if rid not in allowed_ids:
            dropped += 1
            continue
        ts = parse_ts(str(r.get("timestamp", "")))
        prev = latest.get(rid)
        if (prev is None) or (ts >= prev[0]):
            latest[rid] = (ts, r)
        kept += 1
    canon = [rec for _, rec in latest.values()]
    canon.sort(key=lambda x: str(x.get("id", "")))
    print(f"[{mode}] input={len(records)} kept={len(canon)} (dedup from {kept}, dropped={dropped})")
    return canon

def backup_then_write(path: Path, recs: list[dict]):
    if path.exists():
        path.with_suffix(path.suffix + ".bak").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    write_jsonl(path, recs)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default=str(ROOT / "prompts" / "prompts.csv"))
    ap.add_argument("--id-column", default="id")
    ap.add_argument("--general", default=str(RAWDIR / "general.jsonl"))
    ap.add_argument("--instructed", default=str(RAWDIR / "instructed.jsonl"))
    args = ap.parse_args()

    id_list = read_id_set(Path(args.prompts), args.id_column)
    id_set = set(id_list)
    print(f"[prompts] ids={len(id_set)}  sample[0:3]={[id_list[:3]]}")

    g_path = Path(args.general)
    i_path = Path(args.instructed)
    g_recs = load_jsonl(g_path)
    i_recs = load_jsonl(i_path)

    g_canon = canonize_one("general", g_recs, id_set)
    i_canon = canonize_one("instructed", i_recs, id_set)

    backup_then_write(g_path, g_canon)
    backup_then_write(i_path, i_canon)

    print(f"[OK] canonized -> {g_path.name}={len(g_canon)}, {i_path.name}={len(i_canon)}")

if __name__ == "__main__":
    main()