from __future__ import annotations
import argparse, json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def load_summary(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def ensure_outdir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def plot_by_group(summary: dict, out_png: Path):
    data = summary.get("by_group", {})
    labels = []
    vals = []
    for k in ("general", "instructed"):
        if k in data:
            labels.append(k); vals.append(float(data[k]))
    for k, v in data.items():
        if k not in ("general", "instructed"):
            labels.append(k); vals.append(float(v))
    ensure_outdir(out_png)
    plt.figure()
    bars = plt.bar(labels, vals)
    plt.ylim(0, 1)
    plt.title("Compliance rate by group")
    plt.ylabel("rate (0~1)")
    for b, v in zip(bars, vals):
        plt.text(b.get_x()+b.get_width()/2, v+0.02, f"{v*100:.0f}%", ha="center", va="bottom")
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()

def plot_by_group_scenario(summary: dict, out_png: Path):
    d = summary.get("by_group_scenario", {})
    scenarios = sorted({key.split("|", 1)[1] for key in d.keys()}) if d else []
    groups = ["general", "instructed"]
    vals = [[float(d.get(f"{g}|{s}", 0.0)) for g in groups] for s in scenarios]
    ensure_outdir(out_png)
    plt.figure()
    x = range(len(scenarios))
    width = 0.38
    for gi, g in enumerate(groups):
        plt.bar([xi + (gi-0.5)*width for xi in x], [row[gi] for row in vals], width, label=g)
    plt.ylim(0, 1)
    plt.xticks([xi for xi in x], scenarios, rotation=15)
    plt.ylabel("compliance rate (0~1)")
    plt.title("Compliance rate by scenario & group")
    plt.legend()

    for gi in range(len(groups)):
        for xi, s in enumerate(scenarios):
            v = vals[xi][gi]
            plt.text(xi + (gi-0.5)*width, v+0.02, f"{v*100:.0f}%", ha="center", va="bottom")
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()

def main(summary_path: str, outdir: str):
    outdir = Path(outdir)
    s = load_summary(summary_path)
    plot_by_group(s, outdir / "compliance_group.png")
    plot_by_group_scenario(s, outdir / "compliance_by_scenario.png")
    print(f"[OK] saved -> {outdir/'compliance_group.png'} , {outdir/'compliance_by_scenario.png'}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True, help="results/quantitative/compliance_summary.json")
    ap.add_argument("--outdir", default="results/figures")
    a = ap.parse_args()
    main(a.summary, a.outdir)