from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_scores(path: str, metric_key: str, group_key: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    per = data.get("per_item", [])
    groups = {}
    for x in per:
        g = str(x.get(group_key, "unknown"))
        v = float(x[metric_key])
        groups.setdefault(g, []).append(v)
    return groups


def boxplot(groups: dict[str, list[float]], title: str, out_png: Path):
    labels = list(groups.keys())
    vals = [groups[k] for k in labels]
    plt.figure()
    plt.boxplot(vals, labels=labels, showmeans=True)
    plt.title(title)
    plt.ylabel("score")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()


def main(rouge_path: str, bleu_path: str, outdir: str):
    outdir = Path(outdir)
    r_groups = load_scores(rouge_path, "rougeL_f", "prompt_type")
    b_groups = load_scores(bleu_path, "bleu4", "prompt_type")
    boxplot(r_groups, "ROUGE-L F by group", outdir / "box_rougeL.png")
    boxplot(b_groups, "BLEU-4 by group", outdir / "box_bleu4.png")
    print(f"[OK] saved -> {outdir / 'box_rougeL.png'} , {outdir / 'box_bleu4.png'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rouge", required=True)
    ap.add_argument("--bleu", required=True)
    ap.add_argument("--outdir", default="results/figures")
    a = ap.parse_args()
    main(a.rouge, a.bleu, a.outdir)
