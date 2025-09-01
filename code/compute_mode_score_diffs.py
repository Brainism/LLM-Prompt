from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

def _read_json_autodetect(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")

def _extract_score(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, dict):
        for key in ("score", "value", "f1", "f", "metric", "val"):
            if key in val:
                return _safe_float(val[key])
    return float("nan")


def _infer_metric_key(per_item: List[Dict[str, Any]]) -> str:
    if not per_item:
        raise ValueError("per_item is empty")

    preferred = ("rougeL_f", "bleu4", "rougeL", "bleu", "score", "value", "f1", "f")
    sample = per_item[0]

    for k in preferred:
        if k in sample and isinstance(sample[k], (int, float)):
            return k

    for k, v in sample.items():
        if k not in {"id", "prompt_id", "prompt_type", "mode"} and isinstance(
            v, (int, float)
        ):
            return k

    raise ValueError("Unable to infer a numeric metric key from per_item.")

def load_general_instructed_pairs(path: Path) -> Tuple[List[str], np.ndarray, np.ndarray]:
    data = _read_json_autodetect(path)

    ids: List[str] = []
    gen_scores_list: List[float] = []
    inst_scores_list: List[float] = []

    if (
        isinstance(data, dict)
        and "items" in data
        and isinstance(data["items"], list)
        and data["items"]
    ):
        for idx, it in enumerate(data["items"]):
            pid = str(it.get("id") or it.get("prompt_id") or idx)

            if "general" in it and "instructed" in it:
                g_val = _extract_score(it["general"])
                i_val = _extract_score(it["instructed"])
            else:
                modes = it.get("modes", {})
                g_val = _extract_score(modes.get("general"))
                i_val = _extract_score(modes.get("instructed"))

            if not (math.isnan(g_val) or math.isnan(i_val)):
                ids.append(pid)
                gen_scores_list.append(g_val)
                inst_scores_list.append(i_val)

    elif (
        isinstance(data, dict)
        and ("general" in data)
        and ("instructed" in data or "instruct" in data)
    ):
        inst_key = "instructed" if "instructed" in data else "instruct"

        def to_map(x: Any) -> Dict[str, float]:
            if isinstance(x, list):
                m: Dict[str, float] = {}
                for j, item in enumerate(x):
                    pid = str(item.get("id", j)) if isinstance(item, dict) else str(j)
                    score = (
                        _extract_score(item.get("score", item.get("value", item)))
                        if isinstance(item, dict)
                        else _extract_score(item)
                    )
                    m[pid] = score
                return m
            if isinstance(x, dict):
                return {str(k): _extract_score(v) for k, v in x.items()}
            return {}

        gmap = to_map(data["general"])
        imap = to_map(data[inst_key])
        common = sorted(set(gmap) & set(imap))

        ids = common
        gen_scores_list = [gmap[k] for k in common]
        inst_scores_list = [imap[k] for k in common]

    elif isinstance(data, dict) and isinstance(data.get("per_item"), list):
        per = data["per_item"]
        metric_key = _infer_metric_key(per)

        gmap: Dict[str, float] = {}
        imap: Dict[str, float] = {}
        for idx, row in enumerate(per):
            pid = str(row.get("id") or row.get("prompt_id") or idx)
            mode = str(row.get("prompt_type") or row.get("mode") or "").lower()
            val = row.get(metric_key)
            if val is None:
                continue
            if mode.startswith("gen"):
                gmap[pid] = _safe_float(val)
            elif mode.startswith("instr"):
                imap[pid] = _safe_float(val)

        common = sorted(set(gmap) & set(imap))
        ids = common
        gen_scores_list = [gmap[k] for k in common]
        inst_scores_list = [imap[k] for k in common]

    elif (
        isinstance(data, list)
        and data
        and isinstance(data[0], dict)
        and (("general" in data[0]) or ("instructed" in data[0]) or ("instruct" in data[0]))
    ):
        for idx, row in enumerate(data):
            g_val = _extract_score(row.get("general"))
            i_val = _extract_score(row.get("instructed", row.get("instruct")))
            if not (math.isnan(g_val) or math.isnan(i_val)):
                ids.append(str(row.get("id", idx)))
                gen_scores_list.append(g_val)
                inst_scores_list.append(i_val)

    elif (
        isinstance(data, list)
        and data
        and isinstance(data[0], dict)
        and ("score" in data[0])
        and ("system" in data[0] or "model" in data[0])
    ):
        gmap2: Dict[str, float] = {}
        imap2: Dict[str, float] = {}
        for idx, row in enumerate(data):
            pid = str(row.get("id", idx))
            sysname = str(row.get("system", row.get("model", ""))).lower()
            sc = _extract_score(row.get("score"))
            if sysname.startswith("gen"):
                gmap2[pid] = sc
            elif sysname.startswith("instr"):
                imap2[pid] = sc

        common = sorted(set(gmap2) & set(imap2))
        ids = common
        gen_scores_list = [gmap2[k] for k in common]
        inst_scores_list = [imap2[k] for k in common]

    else:
        return [], np.array([]), np.array([])

    gen_arr = np.array(gen_scores_list, dtype=float)
    inst_arr = np.array(inst_scores_list, dtype=float)
    mask = ~(np.isnan(gen_arr) | np.isnan(inst_arr))

    return ids, gen_arr[mask], inst_arr[mask]

def write_differences_csv(
    ids: List[str],
    general: np.ndarray,
    instructed: np.ndarray,
    out_path: Path,
) -> None:

    out_path.parent.mkdir(parents=True, exist_ok=True)
    diffs = instructed - general

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "general", "instructed", "diff"])
        for pid, gv, iv, dv in zip(ids, general, instructed, diffs):
            writer.writerow([pid, f"{gv:.6f}", f"{iv:.6f}", f"{dv:.6f}"])

    mean_diff = float(np.nanmean(diffs)) if diffs.size else float("nan")
    print(f"[OK] wrote {out_path} ({diffs.size} rows). mean_diff={mean_diff:.6f}")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute per-id (instructed - general) score differences and export CSV."
    )
    parser.add_argument("--metric", required=True, help="Path to metric JSON/JSONL file.")
    parser.add_argument("--out", required=True, help="Output CSV path.")
    args = parser.parse_args()

    metric_path = Path(args.metric)
    out_csv = Path(args.out)

    ids, general, instructed = load_general_instructed_pairs(metric_path)
    if not ids:
        write_differences_csv([], np.array([]), np.array([]), out_csv)
        return

    write_differences_csv(ids, general, instructed, out_csv)


if __name__ == "__main__":
    main()