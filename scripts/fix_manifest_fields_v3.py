import argparse, json, re, sys, shutil
from pathlib import Path
from collections import Counter

def load_json(p: Path):
    if not p.exists():
        print(f"[ERR] file not found: {p}", file=sys.stderr); sys.exit(2)
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def guess_lang(text):
    if not text: return "en"
    return "ko" if re.search(r"[가-힣]", text) else "en"

def normalize_len_bin(v):
    if not v: return "medium"
    v = v.strip().lower()
    mapping = {"mid":"medium","med":"medium","m":"medium","short":"short","long":"long","medium":"medium"}
    return mapping.get(v, "medium")

def normalize_diff_bin(v):
    if not v: return "medium"
    v = v.strip().lower()
    mapping = {"easy":"easy","medium":"medium","hard":"hard","e":"easy","h":"hard"}
    return mapping.get(v, "medium")

def sanitize_cluster_id(s):
    if not s: return "GEN"
    out = re.sub(r"[^A-Za-z0-9_\\-]", "_", str(s))
    out = out[:64] if len(out)>64 else out
    if not out:
        return "GEN"
    return out

def sanitize_id(s):
    if not s: return None
    return re.sub(r"\s+", "_", str(s).strip())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--inplace", action="store_true", help="overwrite manifest (create backup)")
    args=ap.parse_args()

    manifest_p = Path(args.manifest)
    schema_p = Path(args.schema)
    if not manifest_p.exists(): 
        print(f"[ERR] manifest not found: {manifest_p}", file=sys.stderr); sys.exit(2)
    if not schema_p.exists():
        print(f"[ERR] schema not found: {schema_p}", file=sys.stderr); sys.exit(2)

    schema = load_json(schema_p)
    try:
        item_schema = schema["properties"]["items"]["items"]
        allowed_props = set(item_schema.get("properties", {}).keys())
        required_props = list(item_schema.get("required", []))
    except Exception as e:
        print(f"[ERR] unexpected schema shape: {e}", file=sys.stderr); sys.exit(3)

    data = load_json(manifest_p)
    items = data.get("items", [])
    if not isinstance(items, list):
        print("[ERR] manifest.items is not a list", file=sys.stderr); sys.exit(4)

    if args.inplace:
        bak = manifest_p.with_suffix(manifest_p.suffix + ".bak")
        shutil.copy2(manifest_p, bak)
        print(f"[OK] backup created: {bak}")

    new_items = []
    for it in items:
        new = {}
        for k,v in it.items():
            if k in allowed_props:
                new[k] = v
        idv = sanitize_id(new.get("id") or it.get("id") or "")
        if not idv:
            idv = f"GEN_{abs(hash(it.get('input','') or json.dumps(it)) ) & 0xffffffff:08x}"
        new["id"] = idv

        if "input" not in new or not new["input"]:
            new["input"] = it.get("input","") or it.get("prompt","") or ""
        if "reference" not in new or not new["reference"]:
            new["reference"] = it.get("reference","") or ""

        if "domain" not in new or not new["domain"]:
            new["domain"] = it.get("domain","general") or "general"

        if "lang" not in new or new["lang"] not in ("ko","en"):
            new["lang"] = guess_lang(new.get("input",""))

        new["len_bin"] = normalize_len_bin(new.get("len_bin") or it.get("len_bin"))

        new["diff_bin"] = normalize_diff_bin(new.get("diff_bin") or it.get("diff_bin"))

        new["cluster_id"] = sanitize_cluster_id(new.get("cluster_id") or it.get("cluster_id") or f"{new['domain']}_{new['lang']}_{new['len_bin']}_{new['diff_bin']}")

        new["license"] = new.get("license") or it.get("license") or "CC-BY-4.0"

        new_items.append(new)

    ids = [x["id"] for x in new_items]
    dup = [k for k,c in Counter(ids).items() if c>1]
    if dup:
        seen = set()
        fixed = []
        counters = {}
        for r in new_items:
            base = r["id"]
            if base not in seen:
                seen.add(base); fixed.append(r)
            else:
                cnt = counters.get(base,1)+1
                counters[base]=cnt
                new_id = f"{base}_{cnt}"
                r["id"]=new_id
                seen.add(new_id); fixed.append(r)
        new_items = fixed

    out = {"items": new_items}
    if args.inplace:
        manifest_p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] manifest updated in place: {manifest_p} (n={len(new_items)})")
    else:
        outp = manifest_p.with_name(manifest_p.stem + ".fixed.json")
        outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] fixed manifest written: {outp} (n={len(new_items)})")

if __name__ == "__main__":
    main()