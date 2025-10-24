#!/usr/bin/env python3
"""
retry_selected_v2.py

Usage (cmd):
  python retry_scripts\retry_selected_v2.py --ids EX-0049 --prompt-file prompts\main.csv --out results\raw\retry_general_EX-0049.jsonl --mode general --model gemma:7b --use-cli --timeout 600
"""
import argparse, csv, subprocess, shlex, os
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--ids", required=True, help="Comma-separated IDs to retry, e.g. EX-0001,EX-0007")
parser.add_argument("--prompt-file", default="prompts/main.csv", help="Original prompts CSV (id,prompt,reference,...)")
parser.add_argument("--out", default="results/raw/retry_selected.jsonl", help="Output JSONL path for infer_via_ollama.py")
parser.add_argument("--mode", choices=["general","instructed"], default="general")
parser.add_argument("--model", default="gemma:7b")
parser.add_argument("--use-cli", action="store_true")
parser.add_argument("--timeout", type=int, default=300)
parser.add_argument("--retries", type=int, default=1)
args = parser.parse_args()

ids_set = set([x.strip() for x in args.ids.split(",") if x.strip()])
orig = Path(args.prompt_file)
if not orig.exists():
    raise SystemExit(f"Prompt file not found: {orig}")

# Read CSV and filter by id column (case-insensitive)
with orig.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f)
    header = next(reader)
    lower_header = [h.strip().lower() for h in header]
    id_col = None
    for candidate in ("id","ID","Id"):
        if candidate.lower() in lower_header:
            id_col = lower_header.index(candidate.lower()); break
    if id_col is None:
        id_col = 0
    rows = [row for row in reader if row and row[id_col].strip() in ids_set]

if not rows:
    raise SystemExit(f"No matching ids found in {orig} for ids={args.ids}")

# write tmp csv
tmp_dir = Path("tmp")
tmp_dir.mkdir(exist_ok=True)
tmp_csv = tmp_dir / f"prompts_filter_{'_'.join(sorted(ids_set))}.csv"
with tmp_csv.open("w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

# build command to call infer_via_ollama.py
cmd = [
    "python", "scripts\\infer_via_ollama.py",
    "--prompt-file", str(tmp_csv),
    "--mode", args.mode,
    "--model", args.model,
    "--out", args.out,
    "--timeout", str(args.timeout),
    "--retries", str(args.retries)
]
if args.use_cli:
    cmd.append("--use-cli")

print("Running:", " ".join(shlex.quote(c) for c in cmd))
ret = subprocess.run(cmd)
if ret.returncode != 0:
    raise SystemExit(f"infer_via_ollama.py returned exit code {ret.returncode}")
print("Done. Output written to", args.out)
