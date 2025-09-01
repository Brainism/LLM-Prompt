import argparse
import json
from pathlib import Path
from typing import Dict, Optional

import matplotlib.pyplot as plt
import pandas as pd


def _read_text_bom_safe(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig")


def _load_as_json(p: Path) -> Optional[dict]:
    try:
        raw = _read_text_bom_safe(p)
        s = raw.lstrip()
        if s.startswith("{") or s.startswith("[") or p.suffix.lower() == ".json":
            return json.loads(s)
        return None
    except Exception:
        return None


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower(): c for c in df.columns}

    def col(*names) -> Optional[str]:
        for n in names:
            if n in lower:
                return lower[n]
        return None

    c_model = col("model")
    c_mode = col("mode")
    c_rule = col("rule", "rule_name", "constraint", "check", "validator")

    c_pass_rate = col("pass_rate", "passratio", "pass")
    c_n_total = col("n_total", "total", "count", "num", "n")
    c_n_pass = col("n_pass", "passed", "ok", "success")
    c_n_fail = col("n_fail", "failed", "fail")

    df = df.copy()
    if c_pass_rate is None:
        if c_n_pass and c_n_total:
            df["pass_rate"] = df[c_n_pass] / df[c_n_total].replace(0, pd.NA)
        elif c_n_pass and c_n_fail:
            denom = (df[c_n_pass].fillna(0) + df[c_n_fail].fillna(0)).replace(0, pd.NA)
            df["pass_rate"] = df[c_n_pass] / denom
        else:
            num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            df["pass_rate"] = pd.NA if not num_cols else df[num_cols[0]]
    else:
        if c_pass_rate != "pass_rate":
            df = df.rename(columns={c_pass_rate: "pass_rate"})

    if c_n_total:
        if c_n_total != "n_total":
            df = df.rename(columns={c_n_total: "n_total"})
    else:
        df["n_total"] = 1

    rename_map: Dict[str, str] = {}
    if c_model and c_model != "model":
        rename_map[c_model] = "model"
    if c_mode and c_mode != "mode":
        rename_map[c_mode] = "mode"
    if c_rule and c_rule != "rule":
        rename_map[c_rule] = "rule"
    if c_n_pass and c_n_pass != "n_pass":
        rename_map[c_n_pass] = "n_pass"
    if c_n_fail and c_n_fail != "n_fail":
        rename_map[c_n_fail] = "n_fail"

    if rename_map:
        df = df.rename(columns=rename_map)

    if "pass_rate" in df.columns:
        df["pass_rate"] = pd.to_numeric(df["pass_rate"], errors="coerce")
    if "n_total" in df.columns:
        df["n_total"] = (
            pd.to_numeric(df["n_total"], errors="coerce").fillna(0).astype(int)
        )

    return df


def load_summary(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"summary not found: {p}")

    obj = _load_as_json(p)
    if obj is not None:
        if isinstance(obj, list):
            df = pd.DataFrame(obj)
        elif isinstance(obj, dict):
            rows = None
            for key in ("items", "rows", "summary", "data"):
                v = obj.get(key)
                if isinstance(v, list):
                    rows = v
                    break
            if rows is None:
                df = pd.DataFrame([obj])
            else:
                df = pd.DataFrame(rows)
    else:
        df = pd.read_csv(p, encoding="utf-8-sig")

    return _normalize_df(df)


def _weighted_pass_rate(g: pd.DataFrame) -> float:
    if "n_total" in g.columns and g["n_total"].sum() > 0 and "pass_rate" in g.columns:
        return float((g["pass_rate"] * g["n_total"]).sum() / g["n_total"].sum())
    return float(g["pass_rate"].mean())


def plot_by_model_mode(df: pd.DataFrame, outdir: Path) -> Optional[Path]:
    if "pass_rate" not in df.columns:
        return None

    have_model = "model" in df.columns
    have_mode = "mode" in df.columns
    if not (have_model or have_mode):
        return None

    keys = [k for k in ("model", "mode") if k in df.columns]

    tmp = df.dropna(subset=["pass_rate"]).copy()
    if "n_total" not in tmp.columns:
        tmp["n_total"] = 1
    tmp["__okw"] = tmp["pass_rate"] * tmp["n_total"]

    agg = (
        tmp.groupby(keys, dropna=False)
        .agg(n_total=("n_total", "sum"), okw=("__okw", "sum"))
        .reset_index()
    )
    if agg.empty:
        return None
    agg["pass_rate"] = agg["okw"] / agg["n_total"].where(agg["n_total"] != 0)
    agg = agg.sort_values(keys, kind="stable")

    if have_model and have_mode:
        labels = [
            f"{m}\n({mo})"
            for m, mo in zip(agg["model"].astype(str), agg["mode"].astype(str))
        ]
        title = "Compliance pass rate by model / mode"
    elif have_model:
        labels = agg["model"].astype(str).tolist()
        title = "Compliance pass rate by model"
    else:
        labels = agg["mode"].astype(str).tolist()
        title = "Compliance pass rate by mode"

    outdir.mkdir(parents=True, exist_ok=True)
    fig_path = outdir / "compliance_passrate_by_model_mode.png"

    plt.figure(figsize=(max(8, 0.8 * len(labels)), 5))
    plt.bar(labels, agg["pass_rate"])
    plt.ylim(0, 1.0)
    plt.ylabel("Pass rate")
    plt.title(title)
    for i, v in enumerate(agg["pass_rate"]):
        plt.text(
            i, min(v + 0.02, 0.98), f"{v:.2f}", ha="center", va="bottom", fontsize=9
        )
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200)
    plt.close()
    return fig_path


def plot_top_fail_rules(
    df: pd.DataFrame, outdir: Path, topk: int = 15
) -> Optional[Path]:
    if "rule" not in df.columns or "pass_rate" not in df.columns:
        return None

    tmp = df.copy()
    tmp = tmp[tmp["rule"].notna()].copy()
    if tmp.empty:
        return None
    tmp["pass_rate"] = pd.to_numeric(tmp["pass_rate"], errors="coerce")
    tmp = tmp.dropna(subset=["pass_rate"])

    if "n_total" not in tmp.columns:
        tmp["n_total"] = 1
    tmp["__okw"] = tmp["pass_rate"] * tmp["n_total"]

    agg = (
        tmp.groupby("rule", dropna=False)
        .agg(n_total=("n_total", "sum"), okw=("__okw", "sum"))
        .reset_index()
    )
    if agg.empty:
        return None
    agg["pass_rate"] = agg["okw"] / agg["n_total"].where(agg["n_total"] != 0)
    agg["fail_rate"] = 1.0 - agg["pass_rate"]
    agg = agg.sort_values("fail_rate", ascending=False).head(topk)

    outdir.mkdir(parents=True, exist_ok=True)
    fig_path = outdir / "compliance_top_fail_rules.png"

    labels = agg["rule"].astype(str)

    plt.figure(figsize=(9, max(4, 0.32 * len(agg))))
    plt.barh(labels, agg["fail_rate"])
    plt.xlim(0, 1.0)
    plt.xlabel("Fail rate")
    plt.title(f"Top-{len(agg)} failing rules")
    for i, v in enumerate(agg["fail_rate"]):
        plt.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=200, bbox_inches="tight")
    plt.close()
    return fig_path


def main(summary_path: str, outdir: str):
    df = load_summary(summary_path)

    out_dir = Path(outdir)
    f1 = plot_by_model_mode(df, out_dir)
    f2 = plot_top_fail_rules(df, out_dir)

    print("[OK] compliance_viz done.")
    print(" - summary rows:", len(df))
    if f1:
        print(" - saved:", f1)
    else:
        print(" - skip: pass rate by model/mode (columns missing)")
    if f2:
        print(" - saved:", f2)
    else:
        print(" - skip: top failing rules (columns missing)")


import sys


def _autodetect_summary() -> str | None:
    candidates = [
        Path(r"results/quantitative/compliance_summary.csv"),
        Path(r"results/quantitative/compliance_summary.json"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    for ext in ("csv", "json"):
        for p in Path("results").rglob(f"*compliance*summary*.{ext}"):
            return str(p)
    return None


from pathlib import Path


def _autodetect_summary() -> str | None:
    candidates = [
        Path(r"results/quantitative/compliance_summary.csv"),
        Path(r"results/quantitative/compliance_summary.json"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    for ext in ("csv", "json"):
        for p in Path("results").rglob(f"*compliance*summary*.{ext}"):
            return str(p)
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--summary", default=None, help="Path to JSON/CSV compliance summary"
    )
    ap.add_argument("--outdir", default=r"results\figures", help="Output directory")
    a = ap.parse_args()

    summary = a.summary or _autodetect_summary()
    if not summary:
        print("[FATAL] --summary 미지정이며 자동 탐지 실패.")
        print("힌트) 먼저 요약 생성:")
        print(
            r"  python code\compliance_eval.py --outputs results\raw --schema schema\split_manifest_main.schema.json --out results\quantitative\compliance_summary.csv"
        )
        sys.exit(2)

    main(summary, a.outdir)
