# file: code/compliance_eval.py
from __future__ import annotations
import argparse, csv, json, sys, re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def _try_scipy_beta():
    try:
        from scipy.stats import beta as _beta
        return _beta
    except Exception:
        return None

def clopper_pearson_95(k: int, n: int) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    _beta = _try_scipy_beta()
    if _beta is not None:
        lo = _beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
        hi = _beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
        return float(lo), float(hi)
    p = k / n
    z = 1.959963984540054
    denom = 1 + z*z/n
    centre = p + z*z/(2*n)
    adj = z * ((p*(1-p) + z*z/(4*n))/n) ** 0.5
    lo = max(0.0, (centre - adj)/denom)
    hi = min(1.0, (centre + adj)/denom)
    return float(lo), float(hi)

_FULLWIDTH = {0x3000: 0x20}
_FULLWIDTH.update({c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)})
_FULLWIDTH_TRANSLATOR = str.maketrans({k: chr(v) for k, v in _FULLWIDTH.items()})
_RX_WS = re.compile(r"\s+")
_RX_DIGIT_GROUP = re.compile(r"(?<=\d)[ ,](?=\d)")
_BULLET = re.compile(r'^(-|\*|•|\d+[.)])\s+')
_CB = re.compile(r"^\s*```(?:[\w+-]+)?\s*(.*?)\s*```\s*$", re.DOTALL)

def _unwrap_fence(s: str) -> str:
    m = _CB.match(s or "")
    return m.group(1) if m else (s or "")

def _parse_json_tolerant(text: str):
    s = _unwrap_fence(text or "").strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        cand = s[i:j+1]
        try:
            return json.loads(cand)
        except Exception:
            pass
    i, j = s.find("["), s.rfind("]")
    if i != -1 and j != -1 and j > i:
        cand = s[i:j+1]
        try:
            return json.loads(cand)
        except Exception:
            pass
    raise ValueError("json_parse_fail")

def normalize_text(s: str | None) -> str:
    if not s:
        return ""
    s = s.translate(_FULLWIDTH_TRANSLATOR)
    s = _RX_DIGIT_GROUP.sub("", s)
    s = _RX_WS.sub(" ", s)
    return s.strip()

def read_prompts(csv_path: Path) -> Dict[str, Dict]:
    meta: Dict[str, Dict] = {}
    tried = [(csv_path, "utf-8"), (csv_path, "utf-8-sig")]
    last_err = None
    for p, enc in tried:
        try:
            with p.open(encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    pid = str(r.get("prompt_id"))
                    if not pid or pid.lower() == "nan":
                        continue
                    meta[pid] = {
                        "scenario": str(r.get("scenario") or "").strip().lower(),
                        "text": r.get("text") or "",
                        "param": str(r.get("param") or ""),
                        "limit": str(r.get("limit") or "").strip(),
                    }
            return meta
        except Exception as e:
            last_err = e
    raise last_err

def parse_params(s: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for token in (s or "").split(";"):
        token = token.strip()
        if not token:
            continue
        if "=" in token:
            k, v = token.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def _load_jsonl_map(p: Path, text_keys=("output","text","generation","output_text")) -> Dict[str,str]:
    m: Dict[str, str] = {}
    with p.open(encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            o = json.loads(ln)
            pid = str(o.get("id") or o.get("prompt_id") or o.get("name"))
            txt = ""
            for k in text_keys:
                if o.get(k) is not None:
                    txt = o[k]; break
            m[pid] = normalize_text(txt)
    return m

def load_outputs(inputs_path: Path) -> List[Dict]:
    items: List[Dict] = []
    gen = inputs_path / "general.jsonl"
    ins = inputs_path / "instructed.jsonl"
    if gen.exists() and ins.exists():
        gmap = _load_jsonl_map(gen)
        imap = _load_jsonl_map(ins)
        ids = sorted(set(gmap) | set(imap))
        for pid in ids:
            if pid in gmap:
                items.append({"id": pid, "mode": "general", "text": gmap[pid]})
            if pid in imap:
                items.append({"id": pid, "mode": "instructed", "text": imap[pid]})
        return items
    if inputs_path.is_dir():
        for p in inputs_path.glob("*.json"):
            try:
                o = json.loads(p.read_text(encoding="utf-8"))
                pid = str(o.get("id"))
                mode = str(o.get("prompt_type") or o.get("mode") or "unknown").lower()
                txt  = normalize_text(o.get("output_text") or o.get("output") or o.get("text") or "")
                if pid:
                    items.append({"id": pid, "mode": mode, "text": txt})
            except Exception:
                continue
        if items:
            return items
    raise FileNotFoundError(f"출력 파일/디렉터리를 찾을 수 없습니다: {inputs_path}")

def load_rules_pattern(rules_dir: Optional[Path]) -> Optional[re.Pattern]:
    if not rules_dir:
        return None
    fp = rules_dir / "forbidden.txt"
    if fp.exists():
        pat = fp.read_text(encoding="utf-8").strip()
        if pat:
            return re.compile(pat, flags=re.IGNORECASE)
    return None

def load_schema_for_scenario(schema_dir: Optional[Path], scenario: str) -> Optional[dict]:
    if not schema_dir:
        return None
    cand = schema_dir / f"{scenario}.json"
    if not cand.exists():
        return None
    try:
        return json.loads(cand.read_text(encoding="utf-8"))
    except Exception:
        return None

def check_format_json(text: str, params: Dict, schema: Optional[dict], fallback_limit: Optional[int]) -> tuple[bool, str]:
    try:
        obj = _parse_json_tolerant(text)
    except Exception:
        return False, "json_parse_fail"

    req = set([k for k in (params.get("keys") or "").split("|") if k])
    if req and set(obj.keys()) != req:
        return False, f"json_keys_mismatch(expected={sorted(req)}, got={sorted(obj.keys())})"

    if schema:
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if ("steps" in props) and ("steps" not in obj):
            schema = None
    if schema:
        try:
            from jsonschema import validate as _validate
            _validate(instance=obj, schema=schema)
        except Exception:
            return False, "json_schema_validation_fail"

    if fallback_limit is not None and "steps" in obj:
        steps = obj["steps"]
        if not isinstance(steps, list):
            return False, "steps_not_list"
        try:
            N = int(fallback_limit)
        except Exception:
            N = None
        if N is not None and len(steps) != N:
            return False, f"steps_len_mismatch(expected={N}, got={len(steps)})"
        if not all(isinstance(x, str) for x in steps):
            return False, "steps_items_not_all_strings"

    return True, "ok"

def check_limit_words(text: str, params: Dict) -> tuple[bool, str]:
    try:
        n = int(params.get("words", "0"))
    except Exception:
        n = 0
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    return (len(words) <= n, f"words={len(words)} <= {n}")

def check_limit_chars(text: str, params: Dict, fallback_limit: Optional[int]) -> tuple[bool, str]:
    limit = params.get("chars")
    try:
        n = int(limit) if limit is not None and str(limit).strip() != "" else int(fallback_limit or 0)
    except Exception:
        n = int(fallback_limit or 0)
    if n <= 0:
        return False, "limit_not_provided"
    return (len(text) <= n, f"chars={len(text)} <= {n}")

def check_bullets(text: str, params: Dict, default_min: int = 3) -> tuple[bool, str]:
    try:
        n = int(params.get("bullets", default_min))
    except Exception:
        n = default_min
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    bullet_lines = [ln for ln in lines if _BULLET.match(ln)]
    return (len(bullet_lines) >= n, f"bullets={len(bullet_lines)} required>={n}")

def check_forbid_terms(text: str, params: Dict, rules_pat: Optional[re.Pattern]) -> tuple[bool, str]:
    if (params.get("forbid") or "").lower() == "digits":
        ok = re.search(r"[0-9]", text) is None
        return (ok, "no_digits_found" if ok else "digits_present")
    if rules_pat is not None:
        ok = rules_pat.search(text) is None
        return (ok, "regex_clean" if ok else "regex_violation")
    return (True, "ok")

def evaluate_item(scenario: str, text: str, params: Dict, *, schema: Optional[dict], rules_pat: Optional[re.Pattern], default_min_bullets: int, fallback_limit: Optional[int]) -> tuple[bool, str]:
    s = (scenario or "").lower().strip()
    if s == "format-json":
        return check_format_json(text, params, schema, fallback_limit)
    if s == "limit-words":
        return check_limit_words(text, params)
    if s == "limit-chars":
        return check_limit_chars(text, params, fallback_limit)
    if s == "bullets":
        return check_bullets(text, params, default_min_bullets)
    if s == "forbid-terms":
        return check_forbid_terms(text, params, rules_pat)
    return False, "unknown_scenario"

def evaluate(inputs_path: Path, prompts_csv: Path, out_json: Path, out_csv: Path, schema_dir: Optional[Path], rules_dir: Optional[Path], default_min_bullets: int = 3, override_bullets: Optional[int] = None, override_ids: Optional[set[str]] = None) -> None:
    meta = read_prompts(prompts_csv)
    items = load_outputs(inputs_path)
    rules_pat = load_rules_pattern(rules_dir)
    rows: List[Dict] = []
    agg: Dict[Tuple[str, str], Dict[str, int]] = {}
    for o in items:
        pid = str(o.get("id"))
        mode = str(o.get("mode") or o.get("prompt_type") or "unknown").lower()
        text = normalize_text(o.get("text") or "")
        info = meta.get(pid, {"scenario": "unknown", "param": "", "limit": ""})
        scenario = info.get("scenario", "unknown").lower()
        params = parse_params(info.get("param", ""))
        if scenario == "bullets" and override_bullets is not None and (override_ids is None or pid in override_ids):
            params = dict(params); params["bullets"] = str(override_bullets)
        schema = load_schema_for_scenario(schema_dir, scenario)
        fallback_limit = int(str(info.get("limit")).strip()) if str(info.get("limit") or "").strip().isdigit() else None
        passed, reason = evaluate_item(scenario, text, params, schema=schema, rules_pat=rules_pat, default_min_bullets=default_min_bullets, fallback_limit=fallback_limit)
        rows.append({"id": pid, "mode": mode, "scenario": scenario, "passed": int(bool(passed)), "reason": reason})
        key = (scenario, mode)
        cur = agg.setdefault(key, {"k": 0, "n": 0})
        cur["n"] += 1
        cur["k"] += int(bool(passed))
    summary_rows: List[Dict] = []
    for (scenario, mode), kn in sorted(agg.items()):
        k, n = kn["k"], kn["n"]
        lo, hi = clopper_pearson_95(k, n)
        acc = k / n if n else 0.0
        summary_rows.append({"scenario": scenario, "mode": mode, "acc": acc, "ci_low": lo, "ci_high": hi, "n": n})
    by_group: Dict[str, float] = {}
    by_scenario: Dict[str, float] = {}
    by_group_scenario: Dict[str, float] = {}
    tmp_group: Dict[str, Dict[str, int]] = {}
    tmp_scn: Dict[str, Dict[str, int]] = {}
    tmp_pair: Dict[Tuple[str, str], Dict[str, int]] = {}
    for r in rows:
        g = r["mode"]; s = r["scenario"]; v = int(r["passed"])
        tmp_group.setdefault(g, {"k":0,"n":0}); tmp_group[g]["k"]+=v; tmp_group[g]["n"]+=1
        tmp_scn.setdefault(s, {"k":0,"n":0});   tmp_scn[s]["k"]+=v;   tmp_scn[s]["n"]+=1
        tmp_pair.setdefault((g,s), {"k":0,"n":0}); tmp_pair[(g,s)]["k"]+=v; tmp_pair[(g,s)]["n"]+=1
    for g, kn in tmp_group.items():
        by_group[g] = (kn["k"]/kn["n"]) if kn["n"] else 0.0
    for s, kn in tmp_scn.items():
        by_scenario[s] = (kn["k"]/kn["n"]) if kn["n"] else 0.0
    for (g,s), kn in tmp_pair.items():
        by_group_scenario[f"{g}|{s}"] = (kn["k"]/kn["n"]) if kn["n"] else 0.0
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary_rows, "legacy": {"by_group": by_group, "by_scenario": by_scenario, "by_group_scenario": by_group_scenario}, "items": rows}, f, ensure_ascii=False, indent=2)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","mode","scenario","passed","reason"])
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] compliance -> {out_json} , {out_csv}")

def find_first(*candidates: Path) -> Optional[Path]:
    for p in candidates:
        if p and (p.is_file() or p.is_dir()):
            return p
    return None

def _looks_like_root(p: Path) -> bool:
    return ((p / "results" / "batch_outputs").exists()
            or ((p / "results").exists() and (p / "prompts").exists())
            or (p / "code").exists())

def search_project_root() -> Path:
    start = Path(__file__).resolve().parent
    for p in [start] + list(start.parents):
        if _looks_like_root(p):
            return p
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if _looks_like_root(p):
            return p
    return cwd

def _rebase(root: Path, p: Optional[Path]) -> Optional[Path]:
    if p is None:
        return None
    return p if p.is_absolute() else (root / p)

def parse_args():
    ap = argparse.ArgumentParser(description="컴플라이언스 평가")
    ap.add_argument("--inputs", type=Path)
    ap.add_argument("--prompts", type=Path)
    ap.add_argument("--schema-dir", type=Path)
    ap.add_argument("--rules-dir", type=Path)
    ap.add_argument("--out-json", type=Path, default=Path("results/quantitative/compliance_summary.json"))
    ap.add_argument("--out-csv",  type=Path, default=Path("results/quantitative/compliance_by_item.csv"))
    ap.add_argument("--min-bullets", type=int, default=3)
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--override-bullets", type=int, help="bullets 요구치 강제 덮어쓰기")
    ap.add_argument("--override-bullets-ids", type=str, help="쉼표로 구분된 id 목록(없으면 전체)")
    ap.add_argument("--print-summary", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    root = search_project_root()
    inputs   = find_first(_rebase(root, args.inputs),   root / "results" / "batch_outputs") if (args.auto or not args.inputs) else _rebase(root, args.inputs)
    prompts  = find_first(_rebase(root, args.prompts),  root / "prompts" / "prompts.csv")   if (args.auto or not args.prompts) else _rebase(root, args.prompts)
    schema_d = find_first(_rebase(root, args.schema_dir), root / "schema")
    rules_d  = find_first(_rebase(root, args.rules_dir),  root / "rules")
    out_json = _rebase(root, args.out_json)
    out_csv  = _rebase(root, args.out_csv)
    if not inputs or not inputs.exists():
        sys.stderr.write(f"❌ 입력을 찾을 수 없습니다 (예: {root / 'results' / 'batch_outputs'}).\n")
        sys.exit(2)
    if not prompts or not prompts.exists():
        sys.stderr.write(f"❌ 프롬프트 CSV를 찾을 수 없습니다 (예: {root / 'prompts' / 'prompts.csv'}).\n")
        sys.exit(2)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    override_ids = set(map(str, args.override_bullets_ids.split(","))) if args.override_bullets_ids else None
    evaluate(inputs, prompts, out_json, out_csv, schema_d, rules_d,
             default_min_bullets=args.min_bullets,
             override_bullets=args.override_bullets, override_ids=override_ids)

    if args.print_summary:
        from math import isfinite
        data = json.loads(out_json.read_text(encoding="utf-8"))
        for r in data["summary"]:
            acc = f"{r['acc']*100:.1f}%"
            lo  = f"{r['ci_low']*100:.1f}%" if isfinite(r["ci_low"]) else "NA"
            hi  = f"{r['ci_high']*100:.1f}%" if isfinite(r["ci_high"]) else "NA"
            print(f"{r['scenario']}: {r['mode']} {acc} [{lo}, {hi}], n={r['n']}")

if __name__ == "__main__":
    main()