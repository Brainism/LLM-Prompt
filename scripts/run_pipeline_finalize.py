import argparse, subprocess, sys, shutil
from pathlib import Path

PY = sys.executable

DEFAULTS = {
    "orig": "results/raw/general.jsonl",
    "retry": "results/raw/retry_general_EX-0049_fixed.jsonl",
    "out":  "results/raw/general_with_retry.jsonl",
    "prompts": "prompts/main.csv",
    "ins": "results/raw/instructed.jsonl",
    "outdir": "results/quantitative",
    "nboot": "50000"
}

def run(cmd, check=True):
    print("[RUN]"," ".join(cmd))
    r = subprocess.run(cmd)
    if check and r.returncode != 0:
        raise SystemExit(f"Command failed (exit {r.returncode}): {' '.join(cmd)}")
    return r.returncode

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--orig", default=DEFAULTS["orig"])
    p.add_argument("--retry", default=DEFAULTS["retry"])
    p.add_argument("--out", default=DEFAULTS["out"])
    p.add_argument("--prompts", default=DEFAULTS["prompts"])
    p.add_argument("--ins", default=DEFAULTS["ins"])
    p.add_argument("--outdir", default=DEFAULTS["outdir"])
    p.add_argument("--nboot", type=int, default=int(DEFAULTS["nboot"]))
    p.add_argument("--skip-plots", action="store_true")
    p.add_argument("--no-bootstrap", action="store_true")
    args = p.parse_args()

    try:
        run([PY, "scripts/merge_with_retry.py", "--orig", args.orig, "--retry", args.retry, "--out", args.out])
        run([PY, "scripts/make_item_metrics_from_raw.py", "--prompts", args.prompts, "--gen", args.out, "--ins", args.ins, "--outdir", args.outdir])
        run([PY, "scripts/per_item_diffs.py"])
        run([PY, "scripts/per_item_summary.py"])
        if not args.skip_plots:
            try:
                import matplotlib
            except Exception:
                print("[WARN] matplotlib not installed. Plots will be skipped. Install with: pip install matplotlib numpy")
            else:
                run([PY, "scripts/plot_metrics.py"])
        if not args.no_bootstrap:
            run([PY, "scripts/recompute_bootstrap.py", "--nboot", str(args.nboot)])
        pvals = Path(args.outdir) / "p_values_input.csv"
        if not pvals.exists():
            simple = Path(args.outdir) / "stats_simple_after_retry.csv"
            if simple.exists():
                print("[INFO] creating p_values_input.csv from stats_simple_after_retry.csv")
                run([PY, "-c", "import csv,sys; r=csv.reader(open('"+str(simple).replace("\\\\","/")+"',encoding='utf-8')); next(r); rows=list(r); open('"+str(pvals).replace("\\\\","/")+"','w',encoding='utf-8').write('metric,p\\n' + '\\n'.join([row[0] + ',' + row[-1] for row in rows]) )"])
            else:
                print("[WARN] p_values_input.csv not found and stats_simple_after_retry.csv missing. compute_qvalues will likely fail.")
        run([PY, "scripts/compute_qvalues.py"])
        run([PY, "scripts/final_report.py"])
        print("[OK] pipeline finished successfully.")
    except SystemExit as e:
        print("[ERROR]", e)
        raise
    except Exception as e:
        print("[ERROR]", e)
        raise

if __name__ == "__main__":
    main()