from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
            if k in v:
                return _to_float(v[k])
    return float("nan")


def _infer_metric_key_from_per_item(per_item: List[dict]) -> str:
    priority = ["rougeL_f", "bleu4", "rougeL", "bleu", "score", "value", "f1", "f"]
    if not per_item:
        raise ValueError("per_item is empty")
    sample = per_item[0]
    for k in priority:
        if k in sample and isinstance(sample[k], (int, float)):
            return k
    for k, v in sample.items():
        if k not in ("id", "prompt_type", "prompt_id", "mode") and isinstance(
            v, (int, float)
        ):
            return k
    raise ValueError("No numeric metric key found in per_item")


def cohen_d_paired(g: np.ndarray, i: np.ndarray) -> float:
    diff = i - g
    sd = np.std(diff, ddof=1) if diff.size > 1 else 0.0
    if sd == 0.0:
        return float("nan")
    return float(np.mean(diff) / sd)


def paired_bootstrap_ci(
    g: np.ndarray, i: np.ndarray, B: int = 10000, alpha: float = 0.05, seed: int = 123
) -> Tuple[float, float]:
    if B <= 0 or g.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    n = len(g)
    idx = rng.integers(0, n, size=(B, n))
    diffs = (i[idx] - g[idx]).mean(axis=1)
    lo = float(np.percentile(diffs, 100 * alpha / 2))
    hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return lo, hi


def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.array(pvals, dtype=float)
    m = p.size
    if m == 0:
        return p
    order = np.argsort(p)
    ranks = np.empty(m, int)
    ranks[order] = np.arange(1, m + 1)
    q = p * m / ranks
    q_sorted = np.minimum.accumulate(q[order][::-1])[::-1]
    qvals = np.empty(m, float)
    qvals[order] = np.clip(q_sorted, 0.0, 1.0)
    return qvals


def _fmt4(x: float) -> str:
    if x != x:  # NaN
        return "nan"
    return f"{x:.4f}"


def load_pairs_arrays(path: Path) -> Tuple[List[str], np.ndarray, np.ndarray]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ids: List[str] = []
    g_list: List[float] = []
    i_list: List[float] = []

    if (
        isinstance(data, dict)
        and "items" in data
        and isinstance(data["items"], list)
        and data["items"]
    ):
        for idx, it in enumerate(data["items"]):
            pid = str(it.get("id") or it.get("prompt_id") or idx)
            if "general" in it and "instructed" in it:
                gv = _extract_score(it["general"])
                iv = _extract_score(it["instructed"])
            else:
                modes = it.get("modes", {})
                gv = _extract_score(modes.get("general"))
                iv = _extract_score(modes.get("instructed"))
            if not (math.isnan(gv) or math.isnan(iv)):
                ids.append(pid)
                g_list.append(gv)
                i_list.append(iv)

    elif (
        isinstance(data, dict)
        and ("general" in data)
        and ("instructed" in data or "instruct" in data)
    ):
        inst_key = "instructed" if "instructed" in data else "instruct"
        g_raw, i_raw = data.get("general"), data.get(inst_key)

        def _as_map(x):
            if isinstance(x, list):
                m = {}
                for j, d in enumerate(x):
                    pid = str(d.get("id", j))
                    m[pid] = _extract_score(d.get("score", d.get("value", d)))
                return m
            elif isinstance(x, dict):
                m = {}
                for k, v in x.items():
                    m[str(k)] = _extract_score(v)
                return m
            return {}

        gmap = _as_map(g_raw)
        imap = _as_map(i_raw)
        common = sorted(set(gmap) & set(imap))
        ids = common
        g_list = [_extract_score(gmap[k]) for k in common]
        i_list = [_extract_score(imap[k]) for k in common]

    elif (
        isinstance(data, dict)
        and "per_item" in data
        and isinstance(data["per_item"], list)
    ):
        per = data["per_item"]
        mkey = _infer_metric_key_from_per_item(per)
        gmap: Dict[str, float] = {}
        imap: Dict[str, float] = {}
        for idx, x in enumerate(per):
            pid = str(x.get("id") or x.get("prompt_id") or idx)
            mode = str(x.get("prompt_type") or x.get("mode") or "").lower()
            val = x.get(mkey)
            if val is None:
                continue
            if mode.startswith("gen"):
                gmap[pid] = _to_float(val)
            elif mode.startswith("instr"):
                imap[pid] = _to_float(val)
        common = sorted(set(gmap) & set(imap))
        ids = common
        g_list = [gmap[k] for k in common]
        i_list = [imap[k] for k in common]

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
        for idx, d in enumerate(data):
            gv = _extract_score(d.get("general"))
            iv = _extract_score(d.get("instructed", d.get("instruct")))
            if not (math.isnan(gv) or math.isnan(iv)):
                ids.append(str(d.get("id", idx)))
                g_list.append(gv)
                i_list.append(iv)

    elif (
        isinstance(data, list)
        and data
        and isinstance(data[0], dict)
        and (("score" in data[0]) and ("system" in data[0] or "model" in data[0]))
    ):
        gmap: Dict[str, float] = {}
        imap: Dict[str, float] = {}
        for idx, d in enumerate(data):
            pid = str(d.get("id", idx))
            sysname = str(d.get("system", d.get("model", ""))).lower()
            sc = _extract_score(d.get("score"))
            if sysname.startswith("gen"):
                gmap[pid] = sc
            elif sysname.startswith("instr"):
                imap[pid] = sc
        common = sorted(set(gmap.keys()) & set(imap.keys()))
        ids = common
        g_list = [gmap[k] for k in common]
        i_list = [imap[k] for k in common]

    else:
        return [], np.array([], float), np.array([], float)

    g = np.array(g_list, dtype=float)
    i = np.array(i_list, dtype=float)
    mask = ~(np.isnan(g) | np.isnan(i))
    return ids, g[mask], i[mask]


def summarize_arrays(
    g: np.ndarray, i: np.ndarray, n_boot: int, do_wilcoxon: bool
) -> Dict:
    diff = i - g
    n = int(diff.size)
    mean_g = float(np.mean(g)) if n else float("nan")
    mean_i = float(np.mean(i)) if n else float("nan")
    mean_diff = float(np.mean(diff)) if n else float("nan")
    delta_pct = float((mean_diff / (mean_g + 1e-12)) * 100) if n else float("nan")
    sd_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0
    d = mean_diff / sd_diff if sd_diff > 0 else float("nan")

    p = float("nan")
    if do_wilcoxon and SCIPY_OK and n > 0 and np.any(diff != 0):
        try:
            p = float(
                wilcoxon(
                    i, g, zero_method="pratt", alternative="two-sided", mode="auto"
                ).pvalue
            )
        except Exception:
            p = float("nan")

    ci_lo, ci_hi = (
        paired_bootstrap_ci(g, i, B=n_boot, alpha=0.05)
        if n_boot
        else (float("nan"), float("nan"))
    )

    return dict(
        n=n,
        mean_base=mean_g,
        mean_instr=mean_i,
        mean_diff=mean_diff,
        delta_pct=delta_pct,
        sd_diff=sd_diff,
        d=d,
        ci_low=ci_lo,
        ci_high=ci_hi,
        p_wilcoxon=p,
    )


def _search_dirs() -> List[Path]:
    here = Path.cwd()
    dirs = [here / "results" / "quantitative"]
    p = here
    for _ in range(3):
        p = p.parent
        dirs.append(p / "results" / "quantitative")
    return [d for d in dirs if d.exists() and d.is_dir()]


def _derive_metric_name(p: Path) -> str:
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        m = obj.get("metric")
        if not m:
            name = p.stem.lower()
            if "rouge" in name:
                m = "ROUGE"
            elif "codebleu" in name or "bleu" in name:
                m = "BLEU"
            elif "chrf" in name:
                m = "chrF"
            else:
                m = p.stem
        return str(m)
    except Exception:
        return p.stem


def _try_loadable(p: Path) -> bool:
    try:
        _ = load_pairs_arrays(p)
        return True
    except Exception:
        return False


def discover_metric_files() -> Dict[str, Path]:
    candidates: Dict[str, Path] = {}
    prefs = {
        "rouge": ["rouge_corpus", "rouge_l_f1_corpus", "rouge", "rouge_l"],
        "bleu": ["bleu_sacre", "bleu", "codebleu"],
        "chrf": ["chrf", "chrf_sacre"],
    }
    for d in _search_dirs():
        for p in sorted(d.glob("*.json")):
            if not _try_loadable(p):
                continue
            name = p.stem.lower()
            bucket = None
            if "rouge" in name:
                bucket = "rouge"
            elif "codebleu" in name or "bleu" in name:
                bucket = "bleu"
            elif "chrf" in name:
                bucket = "chrf"
            if not bucket:
                continue
            if bucket not in candidates:
                candidates[bucket] = p
            else:

                def rank(stem: str, pref: List[str]) -> int:
                    sl = stem.lower()
                    for i, k in enumerate(pref):
                        if k in sl:
                            return i
                    return 99

                if rank(p.stem, prefs[bucket]) < rank(
                    candidates[bucket].stem, prefs[bucket]
                ):
                    candidates[bucket] = p
    return candidates


def print_table(rows: List[Dict]) -> None:
    headers = [
        "metric",
        "n",
        "mean_base",
        "mean_instr",
        "delta",
        "delta_%",
        "d",
        "CI95_low",
        "CI95_high",
        "p",
        "q",
    ]
    colw = {h: max(len(h), 8) for h in headers}
    for r in rows:
        colw["metric"] = max(colw["metric"], len(str(r["metric"])))

    def fmt_row(r: Dict) -> List[str]:
        return [
            str(r["metric"]).ljust(colw["metric"]),
            str(r["n"]).rjust(colw["n"]),
            _fmt4(r["mean_base"]).rjust(colw["mean_base"]),
            _fmt4(r["mean_instr"]).rjust(colw["mean_instr"]),
            _fmt4(r["mean_diff"]).rjust(colw["delta"]),
            _fmt4(r["delta_pct"]).rjust(colw["delta_%"]),
            _fmt4(r["d"]).rjust(colw["d"]),
            _fmt4(r["ci_low"]).rjust(colw["CI95_low"]),
            _fmt4(r["ci_high"]).rjust(colw["CI95_high"]),
            _fmt4(r["p_wilcoxon"]).rjust(colw["p"]),
            _fmt4(r.get("q_fdr", float("nan"))).rjust(colw["q"]),
        ]

    line = " | ".join(
        [
            "metric".ljust(colw["metric"]),
            "n".rjust(colw["n"]),
            "mean_base".rjust(colw["mean_base"]),
            "mean_instr".rjust(colw["mean_instr"]),
            "delta".rjust(colw["delta"]),
            "delta_%".rjust(colw["delta_%"]),
            "d".rjust(colw["d"]),
            "CI95_low".rjust(colw["CI95_low"]),
            "CI95_high".rjust(colw["CI95_high"]),
            "p".rjust(colw["p"]),
            "q".rjust(colw["q"]),
        ]
    )
    print(line)
    print("-" * len(line))
    for r in rows:
        print(" | ".join(fmt_row(r)))


def parse_args():
    ap = argparse.ArgumentParser(
        description="Paired stats (auto-discovery + robust schema loader)."
    )
    ap.add_argument("--rouge", type=Path, help="ROUGE json")
    ap.add_argument("--bleu", type=Path, help="BLEU/CodeBLEU json")
    ap.add_argument("--chrf", type=Path, help="chrF json")
    ap.add_argument(
        "--output", type=Path, default=Path("results/quantitative/stats_summary.csv")
    )
    ap.add_argument(
        "--bootstrap", type=int, default=0, help="bootstrap resamples (0=off)"
    )
    ap.add_argument(
        "--wilcoxon", action="store_true", help="compute Wilcoxon signed-rank p"
    )
    ap.add_argument("--fdr", action="store_true", help="apply BH-FDR across metrics")
    ap.add_argument(
        "--dry-run", action="store_true", help="파일을 쓰지 않고 요약만 출력"
    )
    return ap.parse_args()


def main():
    args = parse_args()

    if not any([args.rouge, args.bleu, args.chrf]):
        discovered = discover_metric_files()
        args.rouge = args.rouge or discovered.get("rouge")
        args.bleu = args.bleu or discovered.get("bleu")
        args.chrf = args.chrf or discovered.get("chrf")

    if args.dry_run:
        print("[auto-discovery]")
        print("  rouge:", args.rouge)
        print("  bleu :", args.bleu)
        print("  chrf :", args.chrf)

    metric_paths: List[Tuple[str, Optional[Path]]] = [
        ("ROUGE", args.rouge),
        ("BLEU", args.bleu),
        ("chrF", args.chrf),
    ]

    rows: List[Dict] = []
    used: List[Path] = []

    for label, p in metric_paths:
        if not p:
            continue
        if not p.exists():
            print(f"[warn] skip {label}: not found -> {p}")
            continue
        ids, g, i = load_pairs_arrays(p)
        res = summarize_arrays(g, i, n_boot=args.bootstrap, do_wilcoxon=args.wilcoxon)
        metric_name = _derive_metric_name(p) or label
        rows.append({"metric": metric_name, "level": "global", **res})
        used.append(p)

    if not rows:
        print("❌ 사용할 지표 파일을 찾지 못했습니다.")
        print(
            "   - 자동 탐색 경로: ./results/quantitative/ (또는 상위 폴더의 동일 경로)"
        )
        print(
            "   - 또는 직접 지정: --rouge path.json --bleu path.json --chrf path.json"
        )
        return

    if args.fdr:
        pvals = np.array([r.get("p_wilcoxon", float("nan")) for r in rows], dtype=float)
        mask = ~np.isnan(pvals)
        q = np.full_like(pvals, np.nan, dtype=float)
        if np.any(mask):
            q[mask] = bh_fdr(pvals[mask])
        for j, r in enumerate(rows):
            r["q_fdr"] = float(q[j]) if not np.isnan(q[j]) else float("nan")

    print_table(rows)

    if not args.dry_run:
        out = args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        cols = [
            "metric",
            "level",
            "n",
            "mean_base",
            "mean_instr",
            "mean_diff",
            "delta_pct",
            "sd_diff",
            "d",
            "ci_low",
            "ci_high",
            "p_wilcoxon",
            "q_fdr",
        ]
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                row = {k: r.get(k, "") for k in cols}
                w.writerow(row)
        print(f"\n[OK] stats -> {out}")
        if used:
            print("used files:")
            for p in used:
                print(" -", p)

    if not SCIPY_OK and args.wilcoxon:
        print(
            "\n[warn] SciPy 미설치로 Wilcoxon p를 계산하지 못했습니다. `pip install scipy` 권장."
        )


if __name__ == "__main__":
    main()
