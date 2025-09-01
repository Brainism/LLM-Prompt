import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAWDIR = ROOT / "results" / "raw"
ARCH = RAWDIR / "_archive"


def parse_ts(s: str) -> float:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0


def load_jsonl(fp: Path):
    text = fp.read_text(encoding="utf-8")
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            yield json.loads(ln)
        except Exception:
            continue


def write_jsonl(fp: Path, records):
    fp.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def main():
    RAWDIR.mkdir(parents=True, exist_ok=True)
    ARCH.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in RAWDIR.glob("*.jsonl"))
    if not files:
        print("[WARN] no jsonl in results/raw")
        return

    latest = {}
    file_mtime = {p: p.stat().st_mtime for p in files}

    for fp in files:
        for rec in load_jsonl(fp):
            mode = rec.get("mode")
            rid = rec.get("id") or rec.get("item_id") or rec.get("example_id")
            if not mode or rid is None:
                if not mode:
                    mode = "instructed" if "instruct" in fp.name.lower() else "general"
            ts = parse_ts(rec.get("timestamp", "")) or file_mtime.get(fp, 0.0)
            key = (mode, str(rid))
            prev = latest.get(key)
            if (prev is None) or (ts >= prev[0]):
                latest[key] = (ts, rec)

    general = [r for (m, _), (_, r) in latest.items() if m == "general"]
    instructed = [r for (m, _), (_, r) in latest.items() if m == "instructed"]

    out_general = RAWDIR / "general.jsonl"
    out_instruct = RAWDIR / "instructed.jsonl"

    if out_general.exists():
        out_general.with_suffix(".jsonl.bak").write_text(
            out_general.read_text(encoding="utf-8"), encoding="utf-8"
        )
    if out_instruct.exists():
        out_instruct.with_suffix(".jsonl.bak").write_text(
            out_instruct.read_text(encoding="utf-8"), encoding="utf-8"
        )

    write_jsonl(out_general, general)
    write_jsonl(out_instruct, instructed)

    for fp in files:
        if fp.name not in {out_general.name, out_instruct.name}:
            fp.rename(ARCH / fp.name)

    print(
        f"[OK] consolidated: general={len(general)}, instructed={len(instructed)}; archived {len(files)-2} files -> {ARCH}"
    )


if __name__ == "__main__":
    main()
