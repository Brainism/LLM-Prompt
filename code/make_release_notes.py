from __future__ import annotations
import argparse, csv, subprocess, textwrap
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""

def read_latency(p: Path) -> dict:
    d = {}
    if p.exists():
        rows = list(csv.DictReader(p.open("r", encoding="utf-8-sig")))
        for r in rows:
            d[r["mode"]] = {
                "count": r["count"],
                "mean_ms": r["mean_ms"],
                "p50_ms": r["p50_ms"],
                "p95_ms": r["p95_ms"],
                "min_ms": r["min_ms"],
                "max_ms": r["max_ms"],
            }
    return d

def git_commit_short() -> str:
    try:
        out = subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=ROOT, text=True).strip()
        return out
    except Exception:
        return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="release tag/version, e.g., v0.3-baseline-lite")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "release_notes_auto.md")
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "results" / "raw_patched")
    args = ap.parse_args()

    metrics_md = read_text(ROOT / "docs" / "metrics_snapshot.md")
    comp_md    = read_text(ROOT / "docs" / "compliance_snapshot.md")
    env_md     = read_text(ROOT / "docs" / "env_table.md")

    latency_csv = ROOT / "results" / "quantitative" / "latency_summary.csv"
    latency = read_latency(latency_csv)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gitsha = git_commit_short()

    body = []
    body.append(f"# Release Notes — {args.version}\n")
    body.append(f"- Generated: {ts}")
    body.append(f"- Commit: `{gitsha}`")
    body.append(f"- Raw dir (final): `{args.raw_dir.as_posix()}`\n")

    if latency:
        g = latency.get("general", {})
        i = latency.get("instructed", {})
        body.append("## Latency Summary\n")
        body.append("| mode | count | mean(ms) | p50 | p95 | min | max |")
        body.append("|---|---:|---:|---:|---:|---:|---:|")
        if g: body.append(f"| general | {g['count']} | {g['mean_ms']} | {g['p50_ms']} | {g['p95_ms']} | {g['min_ms']} | {g['max_ms']} |")
        if i: body.append(f"| instructed | {i['count']} | {i['mean_ms']} | {i['p50_ms']} | {i['p95_ms']} | {i['min_ms']} | {i['max_ms']} |")
        body.append("")

    if metrics_md.strip():
        body.append("## Metrics Snapshot\n")
        body.append(metrics_md.strip() + "\n")

    if comp_md.strip():
        body.append("## Compliance Snapshot\n")
        body.append(comp_md.strip() + "\n")

    if env_md.strip():
        body.append("## Environment Snapshot\n")
        body.append(env_md.strip() + "\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(body), encoding="utf-8")
    print(f"[ok] wrote {args.out}")

if __name__ == "__main__":
    main()