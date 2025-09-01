from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

try:
    import numpy as np
    from scipy.stats import wilcoxon
except Exception:
    np = None
    wilcoxon = None


def find_metric_files(root: Path):
    files = list(root.rglob("*.json")) + list(root.rglob("*.jsonl"))
    buckets = defaultdict(list)
    for f in files:
        key = f.name.lower()
        if "rouge" in key:
            buckets["rouge"].append(f)
        if "bleu" in key:
            buckets["bleu"].append(f)
        if "chrf" in key or "chr_f" in key:
            buckets["chrf"].append(f)
    return buckets


def read_scores(fp: Path):
    items = []
    if fp.suffix == ".jsonl":
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            s = obj.get(
                "score", obj.get("value", obj.get("delta", obj.get("metric", None)))
            )
            if isinstance(s, dict) and "score" in s:
                s = s["score"]
            if s is not None:
                items.append(float(s))
    else:
        obj = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(obj, list):
            for o in obj:
                s = o.get("score", o.get("value", o.get("delta")))
                if s is not None:
                    items.append(float(s))
        elif isinstance(obj, dict):
            for key in ("items", "scores", "values"):
                if key in obj and isinstance(obj[key], list):
                    for o in obj[key]:
                        if isinstance(o, (int, float)):
                            items.append(float(o))
                        elif isinstance(o, dict):
                            s = o.get("score", o.get("value", o.get("delta")))
                            if s is not None:
                                items.append(float(s))
    return items


def paired_bootstrap_ci(deltas, iters=10000, alpha=0.05, rng=None):
    if rng is None:
        rng = random.Random(1234)
    n = len(deltas)
    if n == 0:
        return (math.nan, math.nan, math.nan)
    boots = []
    for _ in range(iters):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        boots.append(mean(sample))
    boots.sort()
    lo = boots[int((alpha / 2) * iters)]
    hi = boots[int((1 - alpha / 2) * iters)]
    return (mean(deltas), lo, hi)


def summarize_bucket(name, files):
    deltas = []
    for f in files:
        try:
            xs = read_scores(f)
            deltas.extend(xs)
        except Exception:
            continue
    if not deltas:
        return {
            "metric": name,
            "n": 0,
            "mean_delta": None,
            "ci95": [None, None],
            "p_wilcoxon": None,
        }
    mu, lo, hi = paired_bootstrap_ci(deltas)
    p = None
    if wilcoxon and len(deltas) >= 5:
        try:
            stat, p = wilcoxon(deltas, alternative="two-sided", zero_method="wilcox")
        except Exception:
            p = None
    return {
        "metric": name,
        "n": len(deltas),
        "mean_delta": mu,
        "ci95": [lo, hi],
        "p_wilcoxon": p,
    }


def fmt_f(x, digits=6):
    try:
        if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
            return ""
        return f"{x:.{digits}f}"
    except Exception:
        return ""


def main(results_dir: str, params_path: str, out_md: str):
    rp = Path(results_dir)
    buckets = find_metric_files(rp)
    summary = []
    for metric in ("rouge", "bleu", "chrf"):
        s = summarize_bucket(metric, buckets.get(metric, []))
        summary.append(s)

    params = (
        Path(params_path).read_text(encoding="utf-8")
        if Path(params_path).exists()
        else "(missing)"
    )
    md = Path(out_md)
    md.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Baseline Reproducibility Log")
    lines.append("")
    lines.append(f"- results dir: `{rp.resolve()}`")
    lines.append(f"- params file: `{Path(params_path).resolve()}`")
    lines.append("")
    lines.append("## Summary (mean ? and 95% CI via paired bootstrap)")
    lines.append("")
    lines.append("| metric | n | mean ? | 95% CI low | 95% CI high | Wilcoxon p |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in summary:
        if s["n"] == 0:
            lines.append(f"| {s['metric']} | 0 |  |  |  |  |")
        else:
            mean_delta = fmt_f(s["mean_delta"])
            lo = fmt_f(s["ci95"][0])
            hi = fmt_f(s["ci95"][1])
            p_str = "" if s["p_wilcoxon"] is None else f"{s['p_wilcoxon']:.4f}"
            lines.append(
                f"| {s['metric']} | {s['n']} | {mean_delta} | {lo} | {hi} | {p_str} |"
            )

    lines.append("")
    lines.append("## Locked Params (YAML)")
    lines.append("```yaml")
    lines.extend(params.splitlines())
    lines.append("```")
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[verify_baseline] wrote {out_md}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results_dir", default="results")
    ap.add_argument("--params", default="configs/baseline_params.yaml")
    ap.add_argument("--out_md", default="docs/baseline_repro_log.md")
    args = ap.parse_args()
    main(args.results_dir, args.params, args.out_md)
