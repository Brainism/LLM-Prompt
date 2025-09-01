import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAWDIR = ROOT / "results" / "raw"


def now_utc_iso():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def patch_file(fp: Path) -> int:
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = fp.with_suffix(fp.suffix + f".{ts}.bak")
    lines = fp.read_text(encoding="utf-8-sig", errors="replace").splitlines()

    out_lines = []
    changed = 0
    for s in lines:
        s = s.strip()
        if not s:
            continue
        try:
            rec = json.loads(s)
        except Exception:
            out_lines.append(s)
            continue

        touched = False

        if "created_at" not in rec:
            rec["created_at"] = now_utc_iso()
            touched = True

        t = rec.get("timing")
        root_ms = rec.get("latency_ms")
        if not isinstance(t, dict):
            if isinstance(root_ms, (int, float)):
                rec["timing"] = {
                    "latency_ms": int(root_ms),
                    "note": "migrated_from_root",
                }
            else:
                rec["timing"] = {"latency_ms": 0, "note": "backfilled_no_measure"}
            touched = True
        elif "latency_ms" not in t:
            if isinstance(root_ms, (int, float)):
                t["latency_ms"] = int(root_ms)
                t.setdefault("note", "migrated_from_root")
            else:
                t["latency_ms"] = 0
                t.setdefault("note", "backfilled_no_measure")
            touched = True

        if touched:
            changed += 1

        out_lines.append(json.dumps(rec, ensure_ascii=False))

    fp.replace(backup)
    fp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return changed


def main():
    if not RAWDIR.exists():
        raise SystemExit(f"[fail] raw dir not found: {RAWDIR}")
    files = sorted(RAWDIR.glob("*.jsonl"))
    if not files:
        print("[warn] no jsonl files found.")
        return
    total = 0
    for f in files:
        c = patch_file(f)
        print(f"[ok] {f.name}: patched {c} record(s)")
        total += c
    print(f"[done] total patched records: {total}")


if __name__ == "__main__":
    main()
