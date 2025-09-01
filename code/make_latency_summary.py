import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAWDIR = ROOT / "results" / "raw"
OUT = ROOT / "results" / "quantitative" / "latency_summary.csv"


def percentile(xs, q):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    if n == 1:
        return float(xs[0])
    idx = (q / 100) * (n - 1)
    i, j = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - i
    return float(xs[i] + (xs[j] - xs[i]) * frac)


def summary_for(path: Path):
    vals = []
    for ln, s in enumerate(
        path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1
    ):
        s = s.strip()
        if not s:
            continue
        try:
            rec = json.loads(s)
            t = rec.get("timing") or {}
            ms = t.get("latency_ms")
            if isinstance(ms, (int, float)):
                vals.append(float(ms))
        except Exception:
            pass
    if not vals:
        return {"count": 0}
    return {
        "count": len(vals),
        "mean_ms": sum(vals) / len(vals),
        "p50_ms": percentile(vals, 50),
        "p95_ms": percentile(vals, 95),
        "min_ms": min(vals),
        "max_ms": max(vals),
    }


def main():
    rows = []
    for name in ["general", "instructed"]:
        fp = RAWDIR / f"{name}.jsonl"
        if fp.exists():
            s = summary_for(fp)
            s["mode"] = name
            rows.append(s)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "mode",
                "count",
                "mean_ms",
                "p50_ms",
                "p95_ms",
                "min_ms",
                "max_ms",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
