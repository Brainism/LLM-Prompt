from __future__ import annotations

import argparse
import csv
import glob
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

def read_text_any(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp949", "mbcs", "euc-kr", "latin1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")


def looks_json(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if s[0] in "[{":
        try:
            json.loads(s)
            return True
        except Exception:
            return False
    return False


def count_bullets(s: str) -> int:
    return len(re.findall(r"(^|\n)\s*(?:[-*•]|\d+\.)\s+", s))


def parse_flag(v: Optional[str]) -> Optional[bool]:
    if v is None:
        return None
    s = v.strip().lower()
    if s in ("1", "true", "y", "yes"):
        return True
    if s in ("0", "false", "n", "no"):
        return False
    return None


def load_apply_map(csv_path: Optional[Path], id_col: str = "id") -> Dict[str, Dict[str, Optional[bool]]]:
    if not csv_path or not csv_path.exists():
        return {}
    m: Dict[str, Dict[str, Optional[bool]]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = (row.get(id_col) or "").strip()
            if not pid:
                continue
            m[pid] = {
                "needs_json": parse_flag(row.get("needs_json")),
                "needs_bullets": parse_flag(row.get("needs_bullets")),
                "needs_length": parse_flag(row.get("needs_length")),
                "needs_forbid": parse_flag(row.get("needs_forbid")),
            }
    return m


def load_forbid_terms(path: Optional[Path]) -> List[str]:
    if not path or not path.exists():
        return []
    txt = read_text_any(path)
    return [t.strip() for t in txt.splitlines() if t.strip()]

@dataclass
class VerifyConfig:
    forbid_terms_path: Optional[Path] = None
    schema_path: Optional[Path] = None


class FallbackVerifier:
    def __init__(self, cfg: VerifyConfig):
        self.terms = load_forbid_terms(cfg.forbid_terms_path)
        self.schema = None
        self.validator = None
        if cfg.schema_path and cfg.schema_path.exists():
            try:
                import jsonschema
                from jsonschema import Draft7Validator  # noqa: F401
                self.schema = json.loads(cfg.schema_path.read_text(encoding="utf-8"))
                self.validator = jsonschema.Draft7Validator(self.schema)
            except Exception:
                self.validator = None

    def check(self, text: str) -> Tuple[bool, List[str]]:
        reasons: List[str] = []
        low = (text or "").lower()
        for t in self.terms:
            if t.lower() in low:
                reasons.append(f"forbidden:{t}")

        if self.validator is not None:
            try:
                obj = json.loads(text)
            except Exception:
                reasons.append("not_json")
            else:
                errs = list(self.validator.iter_errors(obj))
                if errs:
                    reasons.append("jsonschema_invalid")
        elif self.schema is not None:
            reasons.append("jsonschema_missing")

        return (len(reasons) == 0), reasons


def build_verifier(forbid_path: Optional[Path], schema_path: Optional[Path]):
    """
    가능하면 cvd.Verifier 사용, 없으면 FallbackVerifier 사용.
    """
    try:
        from cvd import Verifier  # type: ignore
        v = Verifier(VerifyConfig(str(forbid_path) if forbid_path else None,
                                  str(schema_path) if schema_path else None))
        return v
    except Exception:
        return FallbackVerifier(VerifyConfig(forbid_path, schema_path))

def heuristic_iter_records(jsonl_path: Path) -> Iterable[Dict[str, Any]]:
    with jsonl_path.open("r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except Exception:
                continue
            yield obj


def heuristic_main(
    raw_dir: Path,
    glob_pat: str,
    limit_chars: int,
    bullets_min_n: int,
    limit_items_json: int,
    forbid_terms_path: Optional[Path],
    apply_from_csv: Optional[Path],
    id_col: str,
    out_csv: Path,
) -> None:
    forbid_terms = load_forbid_terms(forbid_terms_path)
    apply_map = load_apply_map(apply_from_csv, id_col=id_col) if apply_from_csv else {}

    rows: List[Dict[str, Any]] = []
    for fp in sorted(raw_dir.glob(glob_pat)):
        mode = fp.stem
        for rec in heuristic_iter_records(fp):
            pid = str(rec.get("id", ""))
            out = rec.get("output", "") or ""
            needs = apply_map.get(
                pid,
                {"needs_json": None, "needs_bullets": None, "needs_length": None, "needs_forbid": None},
            )

            v_format_json = looks_json(out) if needs["needs_json"] is True else None
            v_bullets_min = (count_bullets(out) >= bullets_min_n) if needs["needs_bullets"] is True else None
            v_limit_chars = (len(out) <= limit_chars) if needs["needs_length"] is True else None
            v_forbid_terms = (
                (all(t.lower() not in (out or "").lower() for t in forbid_terms) if forbid_terms else None)
                if needs["needs_forbid"] is True
                else None
            )

            v_limit_items_json = None
            if v_format_json is True:
                try:
                    j = json.loads(out)
                    if isinstance(j, list):
                        v_limit_items_json = (len(j) <= limit_items_json)
                except Exception:
                    v_limit_items_json = False

            rows.append(
                {
                    "mode": mode,
                    "id": pid,
                    "format_json": v_format_json,
                    "limit_chars": v_limit_chars,
                    "bullets_min_n": v_bullets_min,
                    "limit_items_json": v_limit_items_json,
                    "forbid_terms": v_forbid_terms,
                }
            )

    by_mode = {"general": {}, "instructed": {}}
    keys = ["format_json", "limit_chars", "bullets_min_n", "limit_items_json", "forbid_terms"]
    for mode in by_mode.keys():
        subset = [r for r in rows if r["mode"] == mode]
        for k in keys:
            vals = [r[k] for r in subset if r[k] is not None]
            denom = len(vals) or 1
            by_mode[mode][k] = sum(1 for v in vals if v) / denom

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "general_rate", "instructed_rate"])
        w.writeheader()
        for k in keys:
            w.writerow(
                {"metric": k, "general_rate": f"{by_mode['general'].get(k, 0):.3f}", "instructed_rate": f"{by_mode['instructed'].get(k, 0):.3f}"}
            )
    print(f"[OK] heuristic summary -> {out_csv}")

def cvd_main(
    inputs_dir: Path,
    glob_pat: str,
    forbid_path: Optional[Path],
    schema_path: Optional[Path],
    out_csv: Path,
) -> None:
    verifier = build_verifier(forbid_path, schema_path)

    rows: List[Dict[str, Any]] = []
    for fp in glob.glob(str(inputs_dir / glob_pat)):
        pass_cnt = 0
        tot = 0
        reasons_count: Dict[str, int] = {}

        with open(fp, "r", encoding="utf-8") as f:
            for ln in f:
                try:
                    o = json.loads(ln)
                except Exception:
                    continue
                tot += 1
                ok, reasons = verifier.check(o.get("output", "") or "")
                if ok:
                    pass_cnt += 1
                else:
                    for r in reasons:
                        reasons_count[r] = reasons_count.get(r, 0) + 1

        rows.append(
            {
                "file": Path(fp).name,
                "total": tot,
                "pass": pass_cnt,
                "pass_rate": round(pass_cnt / tot, 4) if tot else 0.0,
                "top_fail": (max(reasons_count, key=reasons_count.get) if reasons_count else ""),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "total", "pass", "pass_rate", "top_fail"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[OK] cvd summary -> {out_csv}")

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compliance checker (dual mode: heuristic / cvd)")

    p.add_argument("--mode", choices=["heuristic", "cvd"], required=True)

    p.add_argument("--raw-dir", default="results/raw", help="[heuristic] input dir")
    p.add_argument("--glob", default="*.jsonl", help="[heuristic|cvd] glob pattern")
    p.add_argument("--limit-chars", type=int, default=1000, help="[heuristic] length limit")
    p.add_argument("--bullets-min-n", type=int, default=3, help="[heuristic] min bullets")
    p.add_argument("--limit-items-json", type=int, default=5, help="[heuristic] max items if output is JSON list")
    p.add_argument("--forbid-terms", type=str, default=None, help="[heuristic] newline-separated terms file")
    p.add_argument("--apply-from", type=str, default=None, help="[heuristic] prompts.csv with needs_* flags")
    p.add_argument("--id-col", type=str, default="id", help="[heuristic] id column name in prompts.csv")
    p.add_argument("--out", type=str, required=True, help="output CSV path")

    p.add_argument("--inputs", type=str, default="results/raw", help="[cvd] input dir")
    p.add_argument("--forbid", type=str, default=None, help="[cvd] forbidden terms file")
    p.add_argument("--schema", type=str, default=None, help="[cvd] JSON schema path")

    return p.parse_args()


def main():
    args = parse_args()
    mode = args.mode

    if mode == "heuristic":
        heuristic_main(
            raw_dir=Path(args.raw_dir),
            glob_pat=args.glob,
            limit_chars=args.limit_chars,
            bullets_min_n=args.bullets_min_n,
            limit_items_json=args.limit_items_json,
            forbid_terms_path=Path(args.forbid_terms) if args.forbid_terms else None,
            apply_from_csv=Path(args.apply_from) if args.apply_from else None,
            id_col=args.id_col,
            out_csv=Path(args.out),
        )
    else:
        # cvd
        cvd_main(
            inputs_dir=Path(args.inputs),
            glob_pat=args.glob,
            forbid_path=Path(args.forbid) if args.forbid else None,
            schema_path=Path(args.schema) if args.schema else None,
            out_csv=Path(args.out),
        )


if __name__ == "__main__":
    main()