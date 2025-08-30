import json, re, os, sys, argparse, tempfile

RX_CLUSTER = re.compile(r"^[A-Z0-9_-]+$")

def sanitize_cluster_id(val):
    s = str(val if val is not None else "")
    s = s.upper()
    s = re.sub(r"[^A-Z0-9_-]", "_", s)
    return s or "CLUSTER"

def normalize_diff_bin(val):
    if val is None: return None
    v = str(val).strip().lower()
    if v in {"mid","med","middle"}: return "medium"
    if v in {"easy","medium","hard"}: return v
    return None

def normalize_len_bin(val):
    if val is None: return None
    v = str(val).strip().lower()
    if v in {"mid","med","middle","avg","average"}: return "medium"
    if v in {"short","medium","long"}: return v
    return v

def atomic_write(path, data):
    ddir = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix="manifest.", dir=ddir or ".")
    os.close(fd)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser(description="Fix manifest fields: drop $schema, normalize len_bin(mid→medium), cluster_id, diff_bin.")
    ap.add_argument("manifest", help=r"Path to manifest JSON (e.g., data\manifest\split_manifest_main.json)")
    ap.add_argument("--keep-schema", action="store_true", help="Do NOT drop the top-level $schema key")
    args = ap.parse_args()

    path = args.manifest
    abspath = os.path.abspath(path)
    print("[PATH]", abspath)

    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    if not args.keep_schema and "$schema" in doc:
        doc.pop("$schema", None)
        print("[FIX] dropped top-level $schema")

    items = doc.get("items", [])
    fix_c = fix_d = fix_l = 0

    for it in items:
        if "cluster_id" in it:
            old = it["cluster_id"]
            new = sanitize_cluster_id(old)
            if new != old or not RX_CLUSTER.fullmatch(new or ""):
                it["cluster_id"] = new
                fix_c += 1

        if "diff_bin" in it:
            old = it.get("diff_bin", None)
            new = normalize_diff_bin(old)
            if new != old:
                it["diff_bin"] = new
                fix_d += 1

        if "len_bin" in it:
            old = it.get("len_bin", None)
            new = normalize_len_bin(old)
            if new != old:
                it["len_bin"] = new
                fix_l += 1

    atomic_write(path, doc)

    after = json.load(open(path, "r", encoding="utf-8"))
    rx = RX_CLUSTER
    bad_c = [i for i,it in enumerate(after.get("items",[])) if not rx.fullmatch(str(it.get("cluster_id","")))]
    mid_l = [i for i,it in enumerate(after.get("items",[])) if str(it.get("len_bin","")).lower()=="mid"]

    print(f"[OK] wrote: {path}")
    print(f"[FIX] cluster_id={fix_c}, diff_bin={fix_d}, len_bin={fix_l}, total_items={len(items)}")
    if bad_c:
        print("[WARN] remaining bad cluster_id idx:", bad_c[:10])
    if mid_l:
        print("[WARN] remaining len_bin='mid' idx:", mid_l[:10])

    print("[SAMPLE first5]", [
        (it.get("cluster_id"), it.get("diff_bin"), it.get("len_bin"))
        for it in after.get("items", [])[:5]
    ])

if __name__ == "__main__":
    main()