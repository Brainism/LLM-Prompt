from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_per_item(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("per_item", [])


def paired_vectors(per: list[dict], metric_key: str):
    g, i = {}, {}
    for x in per:
        pid = str(x["id"])
        grp = str(x.get("prompt_type", ""))
        if metric_key not in x:
            continue
        if grp == "general":
            g[pid] = float(x[metric_key])
        elif grp == "instructed":
            i[pid] = float(x[metric_key])
    ids = sorted(set(g.keys()) & set(i.keys()))
    gv = [g[k] for k in ids]
    iv = [i[k] for k in ids]
    return ids, np.array(gv, dtype=float), np.array(iv, dtype=float)


def mean_sem(v: np.ndarray):
    n = len(v)
    mean = float(np.mean(v)) if n else 0.0
    sem = float(np.std(v, ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    return mean, sem, n


def choose_p_and_d(stats_csv: str, metric_name: str):
    if not Path(stats_csv).exists():
        return None, None
    df = pd.read_csv(stats_csv, encoding="utf-8")
    dfm = df[df["metric"] == metric_name]
    p = None
    d = None
    if not dfm.empty:
        row_t = dfm[dfm["test"] == "paired_t"].head(1)
        row_w = dfm[dfm["test"] == "wilcoxon"].head(1)
        if not row_t.empty and pd.notna(row_t["p_value"].values[0]):
            p = float(row_t["p_value"].values[0])
            d = float(row_t["cohens_d"].values[0])
        elif not row_w.empty and pd.notna(row_w["p_value"].values[0]):
            p = float(row_w["p_value"].values[0])
            d = float(row_w["cohens_d"].values[0])
    return p, d


def save_mean_bar(
    metric_label: str, g: np.ndarray, i: np.ndarray, out_png: Path, p=None, d=None
):
    mg, seg, ng = mean_sem(g)
    mi, sei, ni = mean_sem(i)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    bars = plt.bar(["general", "instructed"], [mg, mi], yerr=[seg, sei], capsize=6)
    plt.ylim(0, 1)
    plt.ylabel(metric_label)
    title = f"{metric_label}: mean±SEM (n={min(ng,ni)})"
    if p is not None:
        star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        title += f"  |  p={p:.3g} ({star})"
    if d is not None:
        title += f"  |  d={d:.2f}"
    plt.title(title)
    for b, v in zip(bars, [mg, mi]):
        plt.text(
            b.get_x() + b.get_width() / 2,
            v + 0.02,
            f"{v:.3f}",
            ha="center",
            va="bottom",
        )
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()


def save_paired_lines(
    metric_label: str, ids, g: np.ndarray, i: np.ndarray, out_png: Path
):
    out_png.parent.mkdir(parents=True, exist_ok=True)
    x0, x1 = 0, 1
    plt.figure()
    for k, a, b in zip(ids, g, i):
        plt.plot([x0, x1], [a, b], marker="o", alpha=0.6)
    plt.xlim(-0.5, 1.5)
    plt.ylim(0, 1)
    plt.xticks([x0, x1], ["general", "instructed"])
    plt.ylabel(metric_label)
    plt.title(f"{metric_label}: paired per-item change")
    plt.axhline(0, color="k", lw=0.5)
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()


def save_delta_hist(metric_label: str, g: np.ndarray, i: np.ndarray, out_png: Path):
    delta = i - g
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    plt.hist(delta, bins=8, edgecolor="black")
    plt.axvline(0, color="red", linestyle="--", lw=1)
    plt.xlabel("delta (instructed - general)")
    plt.ylabel("count")
    mu = float(np.mean(delta)) if len(delta) else 0.0
    plt.title(f"{metric_label}: Δ distribution (mean Δ={mu:.3f})")
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()
    return mu


def save_summary_table(
    rouge_ids, g_r, i_r, bleu_ids, g_b, i_b, stats_csv: str, out_csv: Path
):
    rows = []
    for name, ids, g, i, mkey in [
        ("rougeL_f", rouge_ids, g_r, i_r, "ROUGE-L F"),
        ("bleu4", bleu_ids, g_b, i_b, "BLEU-4"),
    ]:
        mg, seg, ng = mean_sem(g)
        mi, sei, ni = mean_sem(i)
        p, d = choose_p_and_d(stats_csv, name)
        rows.append(
            {
                "metric": name,
                "label": mkey,
                "n": min(ng, ni),
                "mean_general": mg,
                "sem_general": seg,
                "mean_instructed": mi,
                "sem_instructed": sei,
                "delta_mean": float(np.mean(i - g))
                if len(g) == len(i) and len(g) > 0
                else 0.0,
                "p_value": p,
                "cohens_d": d,
            }
        )
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8")
    print(f"[OK] table -> {out_csv}")


def main(rouge_json: str, bleu_json: str, stats_csv: str, outdir: str):
    outdir = Path(outdir)

    rouge_per = load_per_item(rouge_json)
    r_ids, g_r, i_r = paired_vectors(rouge_per, "rougeL_f")
    bleu_per = load_per_item(bleu_json)
    b_ids, g_b, i_b = paired_vectors(bleu_per, "bleu4")

    p_r, d_r = choose_p_and_d(stats_csv, "rougeL_f")
    save_mean_bar("ROUGE-L F", g_r, i_r, outdir / "cmp_rouge_bar.png", p_r, d_r)
    save_paired_lines("ROUGE-L F", r_ids, g_r, i_r, outdir / "cmp_rouge_paired.png")
    save_delta_hist("ROUGE-L F", g_r, i_r, outdir / "cmp_rouge_delta.png")

    p_b, d_b = choose_p_and_d(stats_csv, "bleu4")
    save_mean_bar("BLEU-4", g_b, i_b, outdir / "cmp_bleu_bar.png", p_b, d_b)
    save_paired_lines("BLEU-4", b_ids, g_b, i_b, outdir / "cmp_bleu_paired.png")
    save_delta_hist("BLEU-4", g_b, i_b, outdir / "cmp_bleu_delta.png")

    save_summary_table(
        r_ids,
        g_r,
        i_r,
        b_ids,
        g_b,
        i_b,
        stats_csv,
        Path("results/quantitative/compare_summary.csv"),
    )
    print(f"[OK] saved images in {outdir.resolve()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rouge", required=True)
    ap.add_argument("--bleu", required=True)
    ap.add_argument("--stats", required=False, default="results/stats_summary.csv")
    ap.add_argument("--outdir", default="results/figures")
    a = ap.parse_args()
    main(a.rouge, a.bleu, a.stats, a.outdir)
