import argparse
import json
from pathlib import Path
from typing import List, Optional

import pandas as pd

CAND_MODEL = ["model", "model_name"]
CAND_MODE = ["mode", "scenario", "setting"]
CAND_RULE = ["rule", "rule_name", "constraint", "check", "validator"]

CAND_PASS = [
    "pass",
    "passed",
    "ok",
    "success",
    "is_pass",
    "is_ok",
    "is_success",
    "compliant",
    "is_compliant",
    "valid",
    "is_valid",
    "status",
    "result",
    "label",
]

TRUE_STR = {
    "true",
    "1",
    "y",
    "yes",
    "pass",
    "passed",
    "ok",
    "success",
    "compliant",
    "valid",
}
FALSE_STR = {"false", "0", "n", "no", "fail", "failed", "noncompliant", "invalid"}


def _read_json_or_csv(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(obj, list):
            return pd.DataFrame(obj)
        if isinstance(obj, dict):
            for key in ("items", "rows", "data"):
                v = obj.get(key)
                if isinstance(v, list):
                    return pd.DataFrame(v)
            return pd.DataFrame([obj])
        raise ValueError("Unsupported JSON structure")
    return pd.read_csv(path, encoding="utf-8-sig")


def _find_col(df: pd.DataFrame, cands: List[str]) -> Optional[str]:
    lower = {c.lower(): c for c in df.columns}
    for n in cands:
        if n in lower:
            return lower[n]
    return None


def _coerce_pass_series(s: pd.Series) -> pd.Series:
    if (
        pd.api.types.is_bool_dtype(s)
        or pd.api.types.is_integer_dtype(s)
        or pd.api.types.is_float_dtype(s)
    ):
        return s.astype(float) > 0.5
    s2 = s.astype(str).str.strip().str.lower()
    is_true = s2.isin(TRUE_STR)
    is_false = s2.isin(FALSE_STR)
    out = pd.Series([None] * len(s), index=s.index, dtype="object")
    out[is_true] = True
    out[is_false] = False
    return out.fillna(False).astype(bool)


def build_summary(
    df: pd.DataFrame, *, model_col=None, mode_col=None, rule_col=None, pass_col=None
) -> pd.DataFrame:
    model = model_col or _find_col(df, CAND_MODEL)
    mode = mode_col or _find_col(df, CAND_MODE)
    rule = rule_col or _find_col(df, CAND_RULE)
    pcol = pass_col or _find_col(df, CAND_PASS)
    if pcol is None:
        raise SystemExit(
            "[FATAL] pass 여부 컬럼을 찾지 못했습니다. --pass-col 로 지정하세요."
        )

    df = df.copy()
    df["_is_pass"] = _coerce_pass_series(df[pcol])

    groups: List[pd.DataFrame] = []

    if model or mode:
        keys = [c for c in [model, mode] if c]
        g = (
            df.groupby(keys, dropna=False)["_is_pass"]
            .agg(n_pass="sum", n_total="count")
            .reset_index()
        )
        g["n_pass"] = g["n_pass"].astype(int)
        g["n_total"] = g["n_total"].astype(int)
        g["n_fail"] = g["n_total"] - g["n_pass"]
        g["pass_rate"] = g["n_pass"] / g["n_total"].where(g["n_total"] != 0, None)
        rename = {}
        if model and model != "model":
            rename[model] = "model"
        if mode and mode != "mode":
            rename[mode] = "mode"
        g = g.rename(columns=rename)
        groups.append(g)

    if rule:
        g2 = (
            df.groupby([rule], dropna=False)["_is_pass"]
            .agg(n_pass="sum", n_total="count")
            .reset_index()
        )
        g2["n_pass"] = g2["n_pass"].astype(int)
        g2["n_total"] = g2["n_total"].astype(int)
        g2["n_fail"] = g2["n_total"] - g2["n_pass"]
        g2["pass_rate"] = g2["n_pass"] / g2["n_total"].where(g2["n_total"] != 0, None)
        if rule != "rule":
            g2 = g2.rename(columns={rule: "rule"})
        groups.append(g2)

    if not groups:
        tot = int(df["_is_pass"].count())
        ok = int(df["_is_pass"].sum())
        g = pd.DataFrame(
            [
                {
                    "n_pass": ok,
                    "n_fail": tot - ok,
                    "n_total": tot,
                    "pass_rate": (ok / tot) if tot else None,
                }
            ]
        )
        groups.append(g)

    summary = pd.concat(groups, ignore_index=True, sort=False)
    sort_cols = [c for c in ["model", "mode", "rule"] if c in summary.columns] + [
        "-pass_rate"
    ]
    if "pass_rate" in summary.columns:
        summary = summary.sort_values(
            by=[c for c in ["model", "mode", "rule"] if c in summary.columns]
            + ["pass_rate"],
            ascending=[True, True, True, False][: len(sort_cols)],
        )

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--by-item", required=True, help="Path to compliance_by_item (CSV/JSON)"
    )
    ap.add_argument("--out", required=True, help="Output summary CSV")
    ap.add_argument("--model-col")
    ap.add_argument("--mode-col")
    ap.add_argument("--rule-col")
    ap.add_argument("--pass-col", help="Column name for pass boolean/label")
    args = ap.parse_args()

    df = _read_json_or_csv(Path(args.by_item))
    summary = build_summary(
        df,
        model_col=args.model_col,
        mode_col=args.mode_col,
        rule_col=args.rule_col,
        pass_col=args.pass_col,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out, index=False, encoding="utf-8")
    print(f"[OK] wrote summary: {out} (rows={len(summary)})")


if __name__ == "__main__":
    main()
