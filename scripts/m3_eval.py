from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json, argparse, csv

from metrics_lib import (
    normalize_text, compute_rouge,
    compute_bertscore_grouped,
    try_extract_json, validate_json_against_schema,
    scan_forbidden, p50_p95
)

def load_jsonl(path: Path) -> List[dict]:
    items=[]
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items

def save_jsonl(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def write_csv(path: Path, rows: List[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8"); return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/manifest/split_manifest_main.json")
    ap.add_argument("--prompts", default="data/raw/prompts/prompts.jsonl")
    ap.add_argument("--references", default="data/raw/references/references.jsonl")
    ap.add_argument("--outputs", required=True, help="모델 출력 JSONL (필드: id, output[, latency_ms, prompt_tokens, completion_tokens, model_id, prompt_id])")
    ap.add_argument("--forbidden", default="rules/forbidden_terms.txt")
    ap.add_argument("--ie_schema", default="rules/json_schema_main.json")
    ap.add_argument("--run_name", default="run1")
    ap.add_argument("--no-bertscore", dest="no_bertscore", action="store_true")
    ap.add_argument("--prompt_cost_per_1k", type=float, default=0.0)
    ap.add_argument("--completion_cost_per_1k", type=float, default=0.0)
    args = ap.parse_args()

    manifest_content = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    if isinstance(manifest_content, dict):
        if "items" in manifest_content and isinstance(manifest_content["items"], list):
            man = manifest_content["items"]
        else:
            vals = list(manifest_content.values())
            if vals and isinstance(vals[0], dict) and "id" in vals[0]:
                man = vals
            else:
                raise ValueError(f"unexpected manifest structure in {args.manifest}: top-level dict without 'items' or id->meta mapping")
    elif isinstance(manifest_content, list):
        man = manifest_content
    else:
        raise ValueError(f"unexpected manifest JSON type: {type(manifest_content)}")
    pid2meta = {m["id"]: m for m in man}
    
    refs = {d["id"]: d["reference"] for d in load_jsonl(Path(args.references))}
    outs = load_jsonl(Path(args.outputs))

    terms=[]
    fp_forbid = Path(args.forbidden)
    if fp_forbid.exists():
        for line in fp_forbid.read_text(encoding="utf-8").splitlines():
            s=line.strip()
            if s and not s.startswith("#"): terms.append(s)

    item_rows=[]
    lat_list=[]; cost_list=[]
    preds_for_bs=[]; refs_for_bs=[]; langs_for_bs=[]

    for o in outs:
        id_ = str(o.get("id", ""))
        if id_ not in pid2meta or id_ not in refs:
            continue
        meta = pid2meta[id_]
        pred_raw = str(o.get("output",""))
        pred = normalize_text(pred_raw)
        ref  = normalize_text(refs[id_])

        r = compute_rouge(pred, ref)
        row = {
            "id": id_,
            "domain": meta.get("domain",""),
            "lang": meta.get("lang",""),
            "len_bin": meta.get("len_bin",""),
            "diff_bin": meta.get("diff_bin",""),
            "rouge1_f": r["rouge1_f"],
            "rouge2_f": r["rouge2_f"],
            "rougeL_f": r["rougeL_f"],
        }

        json_valid = None; req_keys_rate = None; forbid_violation = None
        if meta.get("domain") == "information_extraction":
            obj, err = try_extract_json(pred_raw)
            if obj is not None:
                ok, present, total, jerr = validate_json_against_schema(obj, Path(args.ie_schema))
                json_valid = bool(ok); req_keys_rate = (present/total) if total>0 else None
            else:
                json_valid = False; req_keys_rate = 0.0
        forbid_violation = scan_forbidden(pred_raw, terms) if terms else False

        row.update({
            "json_valid": json_valid,
            "req_keys_rate": req_keys_rate,
            "forbid_violation": forbid_violation,
        })

        lat_ms = o.get("latency_ms")
        ptok   = o.get("prompt_tokens")
        ctok   = o.get("completion_tokens")
        cost = None
        if ptok is not None or ctok is not None:
            ptok = ptok or 0; ctok = ctok or 0
            cost = (ptok/1000.0)*args.prompt_cost_per_1k + (ctok/1000.0)*args.completion_cost_per_1k
        row.update({"latency_ms": lat_ms, "prompt_tokens": ptok, "completion_tokens": ctok, "cost": cost})

        item_rows.append(row)
        if lat_ms is not None: lat_list.append(float(lat_ms))
        if cost is not None: cost_list.append(float(cost))

        preds_for_bs.append(pred); refs_for_bs.append(ref); langs_for_bs.append(meta.get("lang","en"))

    if not args.no_bertscore:
        try:
            if preds_for_bs and refs_for_bs:
                bs = compute_bertscore_grouped(preds_for_bs, refs_for_bs, langs_for_bs)
                for i, val in enumerate(bs["bertscore_f1"]):
                    item_rows[i]["bertscore_f1"] = val
        except Exception as e:
            for i in range(len(item_rows)):
                item_rows[i]["bertscore_f1"] = None
            print(f"[warn] BERTScore skipped: {e}")
    else:
        for i in range(len(item_rows)):
            item_rows[i]["bertscore_f1"] = None

    out_dir = Path("results")/"metrics"
    save_jsonl(out_dir/f"{args.run_name}_item_metrics.jsonl", item_rows)

    def agg_mean(key):
        vals=[v[key] for v in item_rows if v.get(key) is not None]
        return float(sum(vals)/len(vals)) if vals else None

    lat_p50, lat_p95 = p50_p95([v for v in lat_list])
    cost_p50, cost_p95 = p50_p95([v for v in cost_list])

    summary = {
        "run_name": args.run_name,
        "n_items": len(item_rows),
        "rouge1_f_mean": agg_mean("rouge1_f"),
        "rouge2_f_mean": agg_mean("rouge2_f"),
        "rougeL_f_mean": agg_mean("rougeL_f"),
        "bertscore_f1_mean": agg_mean("bertscore_f1"),
        "json_valid_rate": None,
        "req_keys_rate_mean": None,
        "forbid_violation_rate": None,
        "latency_ms_p50": lat_p50,
        "latency_ms_p95": lat_p95,
        "cost_p50": cost_p50,
        "cost_p95": cost_p95,
    }
    ie_rows = [r for r in item_rows if r["domain"]=="information_extraction"]
    if ie_rows:
        summary["json_valid_rate"] = sum(1 for r in ie_rows if r.get("json_valid") is True)/len(ie_rows)
        reqs = [r.get("req_keys_rate") for r in ie_rows if r.get("req_keys_rate") is not None]
        summary["req_keys_rate_mean"] = (sum(reqs)/len(reqs)) if reqs else None
    summary["forbid_violation_rate"] = sum(1 for r in item_rows if r.get("forbid_violation"))/len(item_rows) if item_rows else None

    write_csv(out_dir/f"{args.run_name}_summary.csv", [summary])
    md_lines = [
        f"# M3 Summary — {args.run_name}",
        "",
        f"- N items: **{summary['n_items']}**",
        f"- ROUGE-L (mean F): **{summary['rougeL_f_mean']:.4f}**" if summary["rougeL_f_mean"] is not None else "- ROUGE-L: n/a",
        f"- BERTScore F1 (mean): **{summary['bertscore_f1_mean']:.4f}**" if summary["bertscore_f1_mean"] is not None else "- BERTScore: skipped",
        f"- JSON valid rate (IE only): **{summary['json_valid_rate']:.3f}**" if summary["json_valid_rate"] is not None else "- JSON valid: n/a",
        f"- Required-keys rate (IE): **{summary['req_keys_rate_mean']:.3f}**" if summary["req_keys_rate_mean"] is not None else "- Required-keys: n/a",
        f"- Forbidden-term violation rate: **{summary['forbid_violation_rate']:.3f}**" if summary["forbid_violation_rate"] is not None else "- Forbidden: n/a",
        f"- Latency p50/p95 (ms): **{summary['latency_ms_p50']} / {summary['latency_ms_p95']}**",
        f"- Cost p50/p95: **{summary['cost_p50']} / {summary['cost_p95']}**",
        "",
        "See also: `results/metrics/*_item_metrics.jsonl`, `*_summary.csv`."
    ]
    (out_dir/f"{args.run_name}_summary.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[m3] wrote {out_dir}/{args.run_name}_item_metrics.jsonl, *_summary.csv, *_summary.md")

if __name__ == "__main__":
    main()