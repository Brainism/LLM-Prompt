from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path
from collections import defaultdict

def read_prompts(csv_path: str):
    import pandas as pd
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    meta = {}
    for _, r in df.iterrows():
        pid = str(r["prompt_id"])
        meta[pid] = {
            "scenario": str(r["scenario"]),
            "param": str(r.get("param",""))
        }
    return meta

def parse_params(s: str) -> dict[str,str]:
    out = {}
    for token in (s or "").split(";"):
        token = token.strip()
        if not token: continue
        if "=" in token:
            k, v = token.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def load_outputs(dirpath: str):
    items = []
    for p in Path(dirpath).glob("*.json"):
        obj = json.loads(p.read_text(encoding="utf-8"))
        items.append(obj)
    return items

def check_format_json(text: str, params: dict) -> tuple[bool,str]:
    try:
        obj = json.loads(text)
    except Exception as e:
        return False, "json_parse_fail"
    req = set((params.get("keys") or "").split("|"))
    req = {k for k in req if k}
    if req and set(obj.keys()) != req:
        return False, f"json_keys_mismatch(expected={sorted(req)}, got={sorted(obj.keys())})"
    return True, "ok"

def check_limit_words(text: str, params: dict) -> tuple[bool,str]:
    try:
        n = int(params.get("words","0"))
    except:
        n = 0
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    return (len(words) == n, f"words={len(words)} expected={n}")

def check_bullets(text: str, params: dict) -> tuple[bool,str]:
    try:
        n = int(params.get("bullets","0"))
    except:
        n = 0
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()!=""]
    ok_lines = [ln for ln in lines if ln.startswith("- ")]
    if len(lines) != len(ok_lines):
        return False, "non_bullet_lines_present"
    return (len(ok_lines) == n, f"bullets={len(ok_lines)} expected={n}")

def check_forbid_terms(text: str, params: dict) -> tuple[bool,str]:
    if params.get("forbid","") == "digits":
        return (re.search(r"[0-9]", text) is None, "digits_forbidden")
    return True, "ok"

def evaluate_item(scenario: str, text: str, params: dict) -> tuple[bool,str]:
    if scenario == "format-json":
        return check_format_json(text, params)
    if scenario == "limit-words":
        return check_limit_words(text, params)
    if scenario == "bullets":
        return check_bullets(text, params)
    if scenario == "forbid-terms":
        return check_forbid_terms(text, params)
    return False, "unknown_scenario"

def evaluate(inputs_dir: str, prompts_csv: str, out_json: str, out_csv: str):
    meta = read_prompts(prompts_csv)
    outs = load_outputs(inputs_dir)

    rows = []
    by_group = defaultdict(lambda: {"ok":0, "total":0})
    by_scn  = defaultdict(lambda: {"ok":0, "total":0})
    by_group_scn = defaultdict(lambda: {"ok":0, "total":0})

    for o in outs:
        pid = str(o.get("id"))
        grp = str(o.get("prompt_type","unknown"))
        text = str(o.get("output_text",""))
        info = meta.get(pid, {"scenario":"unknown","param":""})
        params = parse_params(info.get("param",""))
        passed, reason = evaluate_item(info["scenario"], text, params)

        rows.append({
            "id": pid, "prompt_type": grp, "scenario": info["scenario"],
            "passed": int(passed), "reason": reason
        })

        by_group[grp]["total"] += 1
        by_group[grp]["ok"] += int(passed)
        scn = info["scenario"]
        by_scn[scn]["total"] += 1
        by_scn[scn]["ok"] += int(passed)
        by_group_scn[(grp,scn)]["total"] += 1
        by_group_scn[(grp,scn)]["ok"] += int(passed)

    summary = {
        "by_group": {g: (v["ok"]/v["total"] if v["total"] else 0.0) for g,v in by_group.items()},
        "by_scenario": {s: (v["ok"]/v["total"] if v["total"] else 0.0) for s,v in by_scn.items()},
        "by_group_scenario": {
            f"{g}|{s}": (v["ok"]/v["total"] if v["total"] else 0.0) for (g,s),v in by_group_scn.items()
        }
    }

    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","prompt_type","scenario","passed","reason"])
        w.writeheader()
        w.writerows(rows)

    print(f"[OK] compliance -> {out_json} , {out_csv}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--output-json", default="results/quantitative/compliance_summary.json")
    ap.add_argument("--output-csv",  default="results/quantitative/compliance_by_item.csv")
    return ap.parse_args()

if __name__ == "__main__":
    a = parse_args()
    evaluate(a.inputs, a.prompts, a.output_json, a.output_csv)