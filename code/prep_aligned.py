from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    from scipy.stats import wilcoxon

    SCIPY_OK = True
except Exception:
    SCIPY_OK = False


def _to_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _extract_score(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in ("score", "value", "f1", "f", "metric", "val"):
            if k in v and isinstance(v[k], (int, float, str)):
                return _to_float(v[k])
    return float("nan")


def load_pairs_any(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    if not path or not path.exists():
        return np.array([], dtype=float), np.array([], dtype=float)

    data = json.loads(path.read_text(encoding="utf-8"))

    if (
        isinstance(data, dict)
        and ("general" in data)
        and ("instructed" in data or "instruct" in data)
    ):
        inst_key = "instructed" if "instructed" in data else "instruct"
        gmap = data.get("general", {}) or {}
        imap = data.get(inst_key, {}) or {}
        if not isinstance(gmap, dict) or not isinstance(imap, dict):
            return np.array([], dtype=float), np.array([], dtype=float)
        ids = sorted(set(gmap.keys()) & set(imap.keys()))
        g = np.array([_extract_score(gmap[k]) for k in ids], dtype=float)
        i = np.array([_extract_score(imap[k]) for k in ids], dtype=float)

    elif (
        isinstance(data, list)
        and data
        and isinstance(data[0], dict)
        and (
            ("general" in data[0])
            or ("instructed" in data[0])
            or ("instruct" in data[0])
        )
    ):
        g_list, i_list = [], []
        for d in data:
            inst_val = d.get("instructed", d.get("instruct"))
            g_val = d.get("general")
            if g_val is not None and inst_val is not None:
                g_list.append(_extract_score(g_val))
                i_list.append(_extract_score(inst_val))
        g = np.array(g_list, dtype=float)
        i = np.array(i_list, dtype=float)

    elif (
        isinstance(data, list)
        and data
        and isinstance(data[0], dict)
        and (("score" in data[0]) and ("system" in data[0] or "model" in data[0]))
    ):
        gmap: Dict[str, float] = {}
        imap: Dict[str, float] = {}
        for d in data:
            sid = str(d.get("id"))
            sysname = str(d.get("system", d.get("model", ""))).lower()
            sc = _extract_score(d.get("score"))
            if not sid:
                sid = str(len(gmap) + len(imap))
            if sysname.startswith("gen"):
                gmap[sid] = sc
            elif sysname.startswith("instr"):
                imap[sid] = sc
        ids = sorted(set(gmap.keys()) & set(imap.keys()))
        g = np.array([gmap[k] for k in ids], dtype=float)
        i = np.array([imap[k] for k in ids], dtype=float)

    else:
        return np.array([], dtype=float), np.array([], dtype=float)

    mask = ~(np.isnan(g) | np.isnan(i))
    return g[mask], i[mask]


def cohen_d_paired(g: np.ndarray, i: np.ndarray) -> float:
    diff = i - g
    sd = np.std(diff, ddof=1) if diff.size > 1 else 0.0
    if sd == 0.0:
        return float("nan")
    return float(np.mean(diff) / sd)


def bootstrap_ci(
    diff: np.ndarray, n_boot: int = 10000, alpha: float = 0.05, seed: int = 42
):
    if diff.size == 0 or n_boot <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n = diff.size
    boots = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        boots[b] = float(np.mean(diff[idx]))
    lo = float(np.percentile(boots, 100 * (alpha / 2)))
    hi = float(np.percentile(boots, 100 * (1 - alpha / 2)))
    return lo, hi


def bh_fdr(pvals: List[float]) -> List[float]:
    arr = np.array(pvals, dtype=float)
    m = len(arr)
    order = np.argsort(arr)
    ranks = np.empty(m, dtype=int)
    ranks[order] = np.arange(1, m + 1)
    q = arr * m / ranks
    q_sorted = np.minimum.accumulate(q[order][::-1])[::-1]
    qvals = np.empty(m, dtype=float)
    qvals[order] = q_sorted
    return qvals.tolist()


def summarize_metric(name: str, path: Path, n_boot: int, do_wilcoxon: bool):
    g, i = load_pairs_any(path)
    n = int(g.size)
    out = {
        "metric": name,
        "n": n,
        "general_mean": float(np.mean(g)) if n else float("nan"),
        "instruct_mean": float(np.mean(i)) if n else float("nan"),
        "delta_mean": float(np.mean(i - g)) if n else float("nan"),
        "delta_pct": float((np.mean(i - g) / (np.mean(g) + 1e-12)) * 100)
        if n
        else float("nan"),
        "boot_ci_lo": float("nan"),
        "boot_ci_hi": float("nan"),
        "wilcoxon_p": float("nan"),
        "cohen_d": float("nan"),
    }
    if n >= 2:
        diff = i - g
        lo, hi = (
            bootstrap_ci(diff, n_boot=n_boot)
            if n_boot and n_boot > 0
            else (float("nan"), float("nan"))
        )
        out["boot_ci_lo"], out["boot_ci_hi"] = lo, hi
        out["cohen_d"] = cohen_d_paired(g, i)
        if do_wilcoxon and SCIPY_OK and np.any(diff != 0):
            try:
                stat, p = wilcoxon(
                    i, g, zero_method="wilcox", alternative="two-sided", mode="auto"
                )
                out["wilcoxon_p"] = float(p)
            except Exception:
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bleu", type=str, help="path to bleu json")
    ap.add_argument("--chrf", type=str, help="path to chrf json")
    ap.add_argument("--rouge", type=str, help="path to rouge json")
    ap.add_argument(
        "--output", type=str, default="results/quantitative/stats_summary.csv"
    )
    ap.add_argument(
        "--bootstrap", type=int, default=0, help="num bootstrap samples for CI (0=off)"
    )
    ap.add_argument(
        "--wilcoxon",
        action="store_true",
        help="run Wilcoxon signed-rank test (needs SciPy)",
    )
    ap.add_argument("--fdr", action="store_true", help="apply BH-FDR across metrics")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows, pvals = [], []

    items = []
    if args.bleu:
        items.append(("BLEU", Path(args.bleu)))
    if args.chrf:
        items.append(("chrF", Path(args.chrf)))
    if args.rouge:
        items.append(("ROUGE", Path(args.rouge)))

    for name, p in items:
        if not p.exists():
            print(f"[warn] skip {name}: not found -> {p}")
            continue
        r = summarize_metric(name, p, n_boot=args.bootstrap, do_wilcoxon=args.wilcoxon)
        rows.append(r)
        pvals.append(r.get("wilcoxon_p", float("nan")))

    if args.fdr and rows:
        valid_idx = [
            i
            for i, pv in enumerate(pvals)
            if isinstance(pv, (int, float)) and not math.isnan(pv)
        ]
        if valid_idx:
            qvals = bh_fdr([pvals[i] for i in valid_idx])
            for j, i in enumerate(valid_idx):
                rows[i]["fdr_q"] = float(qvals[j])
        else:
            for r in rows:
                r["fdr_q"] = ""

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "metric",
        "n",
        "general_mean",
        "instruct_mean",
        "delta_mean",
        "delta_pct",
        "boot_ci_lo",
        "boot_ci_hi",
        "wilcoxon_p",
        "fdr_q",
        "cohen_d",
    ]

    if args.dry_run:
        print("[dry-run] would write CSV ->", outp)
        for r in rows:
            print(r)
        return

    with outp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            if "fdr_q" not in r:
                r["fdr_q"] = ""
            w.writerow({k: r.get(k, "") for k in cols})

    print(f"[OK] wrote {outp} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
