import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

METRIC_FILES = {
    'bleu_sacre': Path('results/quantitative/bleu_sacre.json'),
    'rouge': Path('results/quantitative/rouge.json'),
    'chrf': Path('results/quantitative/chrf.json'),
}

OUTDIR = Path('results/quantitative/plots')
OUTDIR.mkdir(parents=True, exist_ok=True)

def load_pairs(path):
    arr = json.load(path.open(encoding='utf-8'))
    pairs = []
    for it in arr:
        try:
            b = float(it.get('base'))
            i = float(it.get('instr'))
            pairs.append((b,i))
        except Exception:
            continue
    return pairs

def plot_metric(name, pairs):
    base = np.array([p[0] for p in pairs])
    instr = np.array([p[1] for p in pairs])
    diffs = instr - base

    plt.figure(figsize=(8,5))
    plt.hist(diffs, bins=20, edgecolor='black')
    plt.title(f'{name} diff histogram (instr - base)')
    plt.xlabel('Difference')
    plt.ylabel('Count')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()
    hist_path = OUTDIR / f'{name}_diff_hist.png'
    plt.savefig(hist_path, dpi=200)
    plt.close()

    plt.figure(figsize=(4,6))
    plt.boxplot(diffs, vert=True, widths=0.45, patch_artist=True)
    plt.title(f'{name} diff boxplot (instr - base)')
    plt.ylabel('Difference')
    plt.grid(True, axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    box_path = OUTDIR / f'{name}_diff_box.png'
    plt.savefig(box_path, dpi=200)
    plt.close()

    stats_path = OUTDIR / f'{name}_diff_stats.txt'
    with stats_path.open('w', encoding='utf-8') as f:
        f.write(f'n={len(diffs)}\nmean_diff={np.mean(diffs):.6f}\nstd_diff={np.std(diffs, ddof=1):.6f}\nmin={np.min(diffs):.6f}\nmax={np.max(diffs):.6f}\n')
    return hist_path, box_path, stats_path

def main():
    for name,path in METRIC_FILES.items():
        if not path.exists():
            print(f"[WARN] missing {path}, skipping {name}")
            continue
        pairs = load_pairs(path)
        if not pairs:
            print(f"[WARN] no valid pairs for {name}")
            continue
        hist, box, stats = plot_metric(name, pairs)
        print(f"[OK] {name} -> {hist}, {box}, stats: {stats}")

if __name__ == "__main__":
    main()