from __future__ import annotations
import argparse
import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime
import re

HANGUL_RE = re.compile(r'[\uac00-\ud7a3]')

def detect_lang(text: str) -> str:
    if not text: return "etc"
    if HANGUL_RE.search(text):
        return "ko"
    if re.search(r'[A-Za-z]', text):
        return "en"
    return "etc"

def choose_len_bin(n_chars: int, short_thr:int, medium_thr:int) -> str:
    if n_chars < short_thr:
        return "short"
    if n_chars <= medium_thr:
        return "medium"
    return "long"

def canonical_id(raw: str, fallback_idx:int) -> str:
    if not raw or not str(raw).strip():
        return f"EX-{fallback_idx:04d}"
    s = str(raw).strip()
    s = s.upper()
    return s

def sha256_hex(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def slug_cluster_id(cid_raw: str, pid: str) -> str:
    if cid_raw and str(cid_raw).strip():
        return str(cid_raw).strip()
    if pid and "-" in pid:
        return pid.split("-")[0]
    return pid

def read_csv_rows(csv_path: Path):
    rows = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append(r)
    return rows

def get_first_existing(row: dict, keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return str(v)
    return ""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, required=True, help="prompts CSV (utf-8)")
    p.add_argument("--out", type=Path, required=True, help="output manifest JSON (split_manifest.json)")
    p.add_argument("--license", type=str, default="CC-BY-4.0", help="default license value")
    p.add_argument("--short-thresh", type=int, default=50, help="short threshold (chars)")
    p.add_argument("--medium-thresh", type=int, default=200, help="medium threshold (chars)")
    p.add_argument("--default-domain", type=str, default="general", help="default domain")
    p.add_argument("--default-diff", type=str, default="medium", choices=["easy","medium","hard"], help="default difficulty bin")
    args = p.parse_args()

    csv_path: Path = args.csv
    out_path: Path = args.out

    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        raise SystemExit(2)

    rows = read_csv_rows(csv_path)
    items = []
    fallback_idx = 1
    seen_ids = set()

    for row in rows:
        raw_id = get_first_existing(row, ["id","ID","prompt_id","promptID","example_id","example"])
        prompt_text = get_first_existing(row, ["input","prompt","instruction","query","text"])
        reference_text = get_first_existing(row, ["reference","answer","target","output_ref","gold"])
        domain = get_first_existing(row, ["domain"]) or args.default_domain
        lang = get_first_existing(row, ["lang"]) or detect_lang(prompt_text or reference_text)
        license_val = get_first_existing(row, ["license"]) or args.license
        cluster_raw = get_first_existing(row, ["cluster_id","cluster","group"])
        diff_bin = get_first_existing(row, ["diff_bin","difficulty","diff"]) or args.default_diff

        pid = canonical_id(raw_id, fallback_idx)
        while pid in seen_ids:
            fallback_idx += 1
            pid = canonical_id(raw_id, fallback_idx)
        seen_ids.add(pid)
        if raw_id == "" or raw_id is None:
            fallback_idx += 1

        n_chars = len((prompt_text or "").strip())
        len_bin = choose_len_bin(n_chars, args.short_thresh, args.medium_thresh)
        cluster_id = slug_cluster_id(cluster_raw, pid)
        prompt_hash = sha256_hex(prompt_text or "")

        item = {
            "id": pid,
            "input": (prompt_text or "").strip(),
            "reference": (reference_text or "").strip(),
            "domain": domain,
            "lang": lang,
            "len_bin": len_bin,
            "diff_bin": diff_bin,
            "cluster_id": cluster_id,
            "license": license_val,
            "n_chars": n_chars,
            "prompt_hash": prompt_hash
        }
        items.append(item)

    manifest = {
        "$schema": "split_manifest_main.schema.json",
        "created_at": datetime.utcnow().isoformat()+"Z",
        "n_items": len(items),
        "items": items
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote {out_path} (n={len(items)})")

if __name__ == "__main__":
    main()