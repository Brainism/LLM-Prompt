import argparse, json, re, hashlib, csv, sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from jsonschema import Draft7Validator

ID_RE = re.compile(r"^[A-Z0-9_-]{3,64}$")
CLUSTER_RE = re.compile(r"^[A-Z0-9]{3,8}$")

def len_bin_from_n(n: int) -> str:
    if n <= 0:
        return "short"
    if 1 <= n <= 70:
        return "short"
    if 71 <= n <= 160:
        return "medium"
    return "long"

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sanitize_id(raw_id: str) -> str:
    if raw_id is None:
        raw_id = ""
    rid = raw_id.upper()
    rid = re.sub(r"[^A-Z0-9_-]", "_", rid)
    if len(rid) < 3:
        rid = f"ID_{sha256_hex(raw_id)[:6].upper()}"
    if len(rid) > 64:
        rid = rid[:64]
    return rid

def sanitize_cluster_id(raw_cid: str, anchor_for_hash: str) -> str:
    if raw_cid is None:
        raw_cid = ""
    cid = raw_cid.upper()
    cid = re.sub(r"[^A-Z0-9]", "", cid)
    if len(cid) < 3 or len(cid) > 8:
        hv = int(sha256_hex(anchor_for_hash), 16)
        num = str(hv % 10**6).zfill(6)
        cid = ("C" + num)[:8]
        if len(cid) < 3:
            cid = (cid + "0"*3)[:3]
    return cid

def coerce_lang(val: str, fallback="en") -> str:
    if isinstance(val, str) and val in {"ko", "en"}:
        return val
    return fallback

def coerce_diff(val: Any) -> str:
    if isinstance(val, str) and val in {"easy", "medium", "hard"}:
        return val
    return "medium"

def ensure_domain(val: Any) -> str:
    if isinstance(val, str) and val.strip():
        return val
    return "general"

def ensure_license(val: Any) -> str:
    if isinstance(val, str) and val.strip():
        return val
    return "unknown"

def validate_schema(obj: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    v = Draft7Validator(schema)
    errs = []
    for e in v.iter_errors(obj):
        path = "$" + "".join([f".{p}" if isinstance(p, str) else f"[{p}]" for p in e.path])
        errs.append(f"{path}: {e.message}")
    return errs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="기존 manifest json 경로")
    ap.add_argument("--out", required=True, help="업그레이드 결과 저장 경로")
    ap.add_argument("--schema", required=True, help="목표 스키마 경로")
    ap.add_argument("--lang-fallback", default="en", choices=["ko","en"])
    ap.add_argument("--log", default="results/quantitative/manifest_upgrade_log.csv")
    ap.add_argument("--dry-run", action="store_true", help="파일 저장 없이 변경 요약만 출력")
    args = ap.parse_args()

    with open(args.inp, "r", encoding="utf-8") as f:
        src = json.load(f)
    with open(args.schema, "r", encoding="utf-8") as f:
        schema = json.load(f)

    items = src.get("items", [])
    if not isinstance(items, list) or len(items) == 0:
        print("[ERR] 입력 items 비어있음/형식 오류")
        sys.exit(2)

    out_items = []
    seen_ids = {}
    log_rows = []
    kept = skipped = fixed = renamed_dups = 0

    for idx, it in enumerate(items, 1):
        raw = dict(it)
        note_changes = []

        _id = sanitize_id(str(it.get("id", "")))
        if not ID_RE.fullmatch(_id):
            note_changes.append(f"id->sanitized({_id})")

        base_id = _id
        if base_id in seen_ids:
            cnt = seen_ids[base_id] + 1
            new_id = base_id
            while new_id in seen_ids:
                new_id = f"{base_id}_DUP{cnt}"
                cnt += 1
                if len(new_id) > 64:
                    new_id = new_id[:64]
            _id = new_id
            seen_ids[base_id] += 1
            seen_ids[_id] = 1
            note_changes.append(f"dup_renamed({base_id}->{_id})")
            renamed_dups += 1
        else:
            seen_ids[base_id] = 1

        lang = coerce_lang(it.get("lang"), fallback=args.lang_fallback)
        if lang != it.get("lang"):
            note_changes.append(f"lang:{it.get('lang')}->${lang}")

        diff_bin = coerce_diff(it.get("diff_bin"))
        if diff_bin != it.get("diff_bin"):
            note_changes.append(f"diff_bin:{it.get('diff_bin')}->{diff_bin}")

        domain = ensure_domain(it.get("domain"))
        license_ = ensure_license(it.get("license"))

        inp_text = it.get("input", "")
        ref_text = it.get("reference", "")
        if not isinstance(inp_text, str) or not inp_text.strip():
            skipped += 1
            log_rows.append({"id": _id, "status": "skipped", "reason": "empty_input"})
            continue

        n_chars = len(inp_text)
        want_len = len_bin_from_n(n_chars)
        cur_len = it.get("len_bin", None)
        if cur_len != want_len:
            note_changes.append(f"len_bin:{cur_len}->{want_len}")

        raw_cid = it.get("cluster_id", "")
        cluster_id = sanitize_cluster_id(str(raw_cid), anchor_for_hash=_id)
        if raw_cid != cluster_id:
            note_changes.append(f"cluster_id:{raw_cid}->{cluster_id}")

        prompt_hash = sha256_hex(inp_text)

        rec = {
            "id": _id,
            "input": inp_text,
            "reference": ref_text if isinstance(ref_text, str) else "",
            "domain": domain,
            "lang": lang,
            "len_bin": want_len,
            "diff_bin": diff_bin,
            "cluster_id": cluster_id,
            "license": license_,
            "prompt_hash": prompt_hash,
            "n_chars": n_chars
        }

        errs = validate_schema({"items":[rec]}, schema)
        if errs:
            skipped += 1
            log_rows.append({"id": _id, "status": "skipped", "reason": "schema_error", "detail": "; ".join(errs)})
            continue

        out_items.append(rec)
        kept += 1
        if note_changes:
            fixed += 1
        log_rows.append({
            "id": _id,
            "status": "kept",
            "changes": "; ".join(note_changes) if note_changes else ""
        })

    out_obj = {"items": out_items}

    all_errs = validate_schema(out_obj, schema)
    if all_errs:
        print("[ERR] 전체 스키마 검증 실패:")
        for i, e in enumerate(all_errs, 1):
            print(f"{i:03d}) {e}")
        sys.exit(3)

    if args.dry_run:
        print(f"[DRY-RUN] total={len(items)} kept={kept} skipped={skipped} fixed={fixed} dup_renamed={renamed_dups}")
        return

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)
    print(f"[OK] wrote {args.out}  items={len(out_items)}  (from {len(items)})")

    Path(args.log).parent.mkdir(parents=True, exist_ok=True)
    with open(args.log, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id","status","changes","reason","detail"])
        w.writeheader()
        for r in log_rows:
            for k in ["changes","reason","detail"]:
                if k not in r: r[k] = ""
            w.writerow(r)
    print(f"[OK] wrote log {args.log}")
    print(f"[SUMMARY] total={len(items)} kept={kept} skipped={skipped} fixed={fixed} dup_renamed={renamed_dups}")

if __name__ == "__main__":
    main()