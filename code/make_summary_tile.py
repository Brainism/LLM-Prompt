from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
IN_SUMMARY = REPO / "results" / "quantitative" / "compare_summary.csv"
IN_COMPLIANCE = REPO / "results" / "quantitative" / "compliance_summary.json"
OUT = REPO / "results" / "figures" / "summary_tile.png"


def _fmt_p(p):
    try:
        return "p=NA" if p is None or math.isnan(float(p)) else f"p={float(p):.4g}"
    except Exception:
        return "p=NA"


def _fmt_d(d):
    try:
        return "d=NA" if d is None or math.isnan(float(d)) else f"d={float(d):.2f}"
    except Exception:
        return "d=NA"


def draw_metric_bar(ax, row):
    means = [float(row["mean_general"]), float(row["mean_instructed"])]
    sems = [float(row["sem_general"]), float(row["sem_instructed"])]
    bars = ax.bar(["general", "instructed"], means, yerr=sems, capsize=6)
    ax.set_ylim(0, 1)
    ax.set_ylabel(row["label"])
    title = f'{row["label"]}: mean짹SEM (n={int(row["n"])})  |  {_fmt_p(row.get("p_value"))}  |  {_fmt_d(row.get("cohens_d"))}'
    ax.set_title(title)
    for b, v in zip(bars, means):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.02,
            f"{v:.3f}",
            ha="center",
            va="bottom",
        )


def draw_compliance_group(ax, comp):
    g = comp.get("by_group", {})
    labels, vals = [], []
    for k in ("general", "instructed"):
        if k in g:
            labels.append(k)
            vals.append(float(g[k]))
    for k, v in g.items():
        if k not in ("general", "instructed"):
            labels.append(k)
            vals.append(float(v))
    bars = ax.bar(labels, vals)
    ax.set_ylim(0, 1)
    ax.set_ylabel("compliance rate (0??)")
    ax.set_title("Compliance rate by group")
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 0.02,
            f"{v*100:.0f}%",
            ha="center",
            va="bottom",
        )


def draw_compliance_by_scn(ax, comp):
    d = comp.get("by_group_scenario", {})
    scenarios = sorted({k.split("|", 1)[1] for k in d}) if d else []
    groups = ["general", "instructed"]
    x = list(range(len(scenarios)))
    width = 0.38
    for gi, g in enumerate(groups):
        vals = [float(d.get(f"{g}|{s}", 0.0)) for s in scenarios]
        ax.bar([xi + (gi - 0.5) * width for xi in x], vals, width, label=g)
        for xi, v in zip(x, vals):
            ax.text(
                xi + (gi - 0.5) * width,
                v + 0.02,
                f"{v*100:.0f}%",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    ax.set_ylim(0, 1)
    ax.set_xticks(x, scenarios, rotation=15)
    ax.set_ylabel("compliance rate (0??)")
    ax.set_title("Compliance by scenario & group")
    ax.legend()


def main():
    print(f"[INFO] REPO        = {REPO}")
    print(f"[INFO] INPUT CSV   = {IN_SUMMARY}  (exists={IN_SUMMARY.exists()})")
    print(f"[INFO] INPUT JSON  = {IN_COMPLIANCE}  (exists={IN_COMPLIANCE.exists()})")
    if not IN_SUMMARY.exists() or not IN_COMPLIANCE.exists():
        print("[ERROR] ?낅젰 ?뚯씪???놁뒿?덈떎. ??寃쎈줈瑜??뺤씤?섏꽭??")
        sys.exit(1)

    df = pd.read_csv(IN_SUMMARY, encoding="utf-8")
    comp = json.loads(IN_COMPLIANCE.read_text(encoding="utf-8"))
    if df.empty:
        print("[ERROR] compare_summary.csv 媛 鍮꾩뼱 ?덉뒿?덈떎.")
        sys.exit(2)
    need = {"rougeL_f", "bleu4"}
    have = set(df["metric"].unique().tolist())
    if not need.issubset(have):
        print(f"[ERROR] compare_summary.csv???꾩슂??metric???놁뒿?덈떎. have={have}")
        sys.exit(3)

    r = df[df["metric"] == "rougeL_f"].iloc[0].to_dict()
    b = df[df["metric"] == "bleu4"].iloc[0].to_dict()

    print("[INFO] 洹몃┝ ?앹꽦 以묅?)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    draw_metric_bar(axes[0, 0], b)
    draw_metric_bar(axes[0, 1], r)
    draw_compliance_group(axes[1, 0], comp)
    draw_compliance_by_scn(axes[1, 1], comp)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print(f"[OK] saved -> {OUT}")


if __name__ == "__main__":
    main()
