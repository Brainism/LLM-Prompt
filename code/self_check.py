import sys
from pathlib import Path
from subprocess import run

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ok = True


def echo(s):
    print(s, flush=True)


def check_cmd(cmd, name):
    global ok
    r = run(cmd, shell=True)
    if r.returncode == 0:
        echo(f"[OK] {name}")
    else:
        echo(f"[FAIL] {name} (rc={r.returncode})")
        ok = False


man = ROOT / "data/manifest/split_manifest_main.json"
sch = ROOT / "schema/split_manifest_main.schema.json"
echo(f"manifest: {man.exists()}  schema: {sch.exists()}")
if man.exists() and sch.exists():
    check_cmd(
        f'python scripts\\validate_manifest.py --manifest "{man}" --schema "{sch}" --max-errors 50',
        "schema validation",
    )

stats = ROOT / "results/quantitative/stats_summary.csv"
if stats.exists():
    df = pd.read_csv(stats, encoding="utf-8-sig")
    need = {
        "metric",
        "n",
        "mean_diff",
        "ci_lo",
        "ci_hi",
        "stat_or_z",
        "p",
        "q_fdr",
        "cohens_d",
    }
    echo(
        f"[OK] stats_summary exists; cols_ok={need.issubset(df.columns)} rows={len(df)}"
    )
else:
    echo("[WARN] stats_summary.csv missing")

summ = ROOT / "results/quantitative/compliance_summary.csv"
if summ.exists():
    df = pd.read_csv(summ, encoding="utf-8-sig")
    echo(f"[OK] compliance_summary exists; cols={list(df.columns)} rows={len(df)}")
else:
    echo("[WARN] compliance_summary.csv missing")

f1 = ROOT / "results/figures/compliance_passrate_by_model_mode.png"
f2 = ROOT / "results/figures/compliance_top_fail_rules.png"
echo(
    f"figures: passrate={'OK' if f1.exists() else 'MISS'}, rules={'OK' if f2.exists() else 'MISS'}"
)

sys.exit(0 if ok else 1)
