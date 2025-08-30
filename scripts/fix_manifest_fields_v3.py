import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List

RX_CLUSTER = re.compile(r"^[A-Z0-9_-]+$")
LEN_SHORT_MAX = 70
LEN_MED_MIN, LEN_MED_MAX = 71, 160
LEN_LONG_MIN = 161

def bucket_from_n_chars(n: int) -> str:
    if n <= LEN_SHORT_MAX:
        return "short"
    if LEN_MED_MIN <= n <= LEN_MED_MAX:
        return "medium"
    return "long"

def sanitize_cluster_id(val: Any) -> str:
    s = str(val if val is not None else "")
    s = s.upper()
    s = re.sub(r"[^A-Z0-9_-]", "_", s)
    return s or "CLUSTER"

def normalize_diff_bin(val: Any, *, allow_null: bool) -> Any:
    if val is None:
        return None if allow_null else "medium"
    v = str(val).strip().lower()
    if v in {"mid", "med", "middle"}:
        return "medium"
    if v in {"easy", "medium", "hard"}:
        return v
    return None if allow_null else "medium"

def normalize_len_bin(val: Any) -> str:
    if val is None:
        return "medium"
    v = str(val).strip().lower()
    if v in {"mid", "med", "middle", "avg", "average"}:
        return "medium"
    if v in {"short", "medium", "long"}:
        return v
    return "medium"

def sha256_hex(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()

def atomic_write(path: str, data: Dict):
    ddir = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix="manifest.", dir=ddir)
    os.close(fd)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser(description="Fix manifest fields: drop $schema, normalize len_bin/diff_bin, cluster_id, n_chars, prompt_hash.")
    ap.add_argument("manifest", help=r"Path to manifest JSON (e.g., data\manifest\split_manifest_main.json)")

    ap.add_argument("--keep-schema", action="store_true", help="Do NOT drop the top-level $schema key")
    ap.add_argument("--out", type=str, default=None, help="Output path (default: input.with .fixed.json)")
    ap.add_argument("--inplace", action="store_true", help="Overwrite input file in place")

    g = ap.add_mutually_exclusive_group()
    g.add_argument("--allow-null-diff", action="store_true", help="Unknown diff_bin -> null (default)")
    g.add_argument("--strict-diff", action="store_true", help="Unknown diff_bin -> 'medium'")

    ap.add_argument("--add-prompt-hash", action="store_true", help="Add/refresh prompt_hash (sha256 of input)")
    ap.add_argument("--derive-n-chars", action="store_true", default=True, help="Derive n_chars from input length (default on)")
    ap.add_argument("--no-derive-n-chars", dest="derive_n_chars", action="store_false", help="Disable deriving n_chars")

    ap.add_argument("--auto-len-bin", action="store_true", help="Adjust len_bin from n_chars bucket when mismatched")
    ap.add_argument("--auto-n-chars", action="store_true", help="Clamp n_chars to len_bin bucket (NOT recommended)")

    args = ap.parse_args()

    in_path = os.path.abspath(args.manifest)
    if args.inplace and args.out:
        print("[ERR] --inplace and --out are mutually exclusive.", file=sys.stderr)
        sys.exit(2)
    out_path = in_path if args.inplace else (args.out or (os.path.splitext(in_path)[0] + ".fixed.json"))

    print("[PATH] input :", in_path)
    print("[PATH] output:", out_path)

    with open(in_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    if not args.keep_schema and isinstance(doc, dict) and "$schema" in doc:
        doc.pop("$schema", None)
        print("[FIX] dropped top-level $schema")

    items: List[Dict[str, Any]] = doc.get("items", [])
    if not isinstance(items, list):
        print("[ERR] 'items' must be a list.", file=sys.stderr)
        sys.exit(2)

    fix_c = fix_d = fix_l = 0
    set_n = set_h = 0
    warn_len_mismatch = 0
    auto_len_applied = auto_n_applied = 0

    allow_null = True
    if args.strict_diff:
        allow_null = False
    elif args.allow_null_diff:
        allow_null = True

    for it in items:
        old_c = it.get("cluster_id")
        new_c = sanitize_cluster_id(old_c)
        if new_c != old_c or not RX_CLUSTER.fullmatch(new_c or ""):
            it["cluster_id"] = new_c
            fix_c += 1

        if "diff_bin" in it:
            old_d = it.get("diff_bin", None)
            new_d = normalize_diff_bin(old_d, allow_null=allow_null)
            if new_d != old_d:
                it["diff_bin"] = new_d
                fix_d += 1

        old_l = it.get("len_bin", None)
        new_l = normalize_len_bin(old_l)
        if new_l != old_l:
            it["len_bin"] = new_l
            fix_l += 1

        if args.derive_n_chars:
            inp = it.get("input", "")
            if inp is not None:
                n = len(str(inp))
                old_n = it.get("n_chars")
                if old_n != n:
                    it["n_chars"] = n
                    set_n += 1

        if args.add_prompt_hash:
            inp = it.get("input", "")
            if inp is not None:
                h = sha256_hex(str(inp))
                if it.get("prompt_hash") != h:
                    it["prompt_hash"] = h
                    set_h += 1

        n = it.get("n_chars")
        lb = it.get("len_bin")
        if isinstance(n, int) and isinstance(lb, str):
            expected = bucket_from_n_chars(n)
            if expected != lb:
                warn_len_mismatch += 1
                if args.auto_len_bin:
                    it["len_bin"] = expected
                    auto_len_applied += 1
                elif args.auto_n_chars:
                    if lb == "short":
                        it["n_chars"] = min(n, LEN_SHORT_MAX)
                    elif lb == "medium":
                        it["n_chars"] = max(LEN_MED_MIN, min(n, LEN_MED_MAX))
                    else:  # long
                        it["n_chars"] = max(n, LEN_LONG_MIN)
                    auto_n_applied += 1

    out_doc = {"items": items}
    atomic_write(out_path, out_doc)

    with open(out_path, "r", encoding="utf-8") as f:
        after = json.load(f)

    bad_c = [i for i, it in enumerate(after.get("items", []))
             if not RX_CLUSTER.fullmatch(str(it.get("cluster_id", "")))]
    mid_l = [i for i, it in enumerate(after.get("items", []))
             if str(it.get("len_bin", "")).lower() in {"mid"}]

    print(f"[OK] wrote: {out_path}")
    print(f"[FIX] cluster_id={fix_c}, diff_bin={fix_d}, len_bin={fix_l}, "
          f"n_chars_set={set_n}, prompt_hash_set={set_h}, total_items={len(items)}")
    if warn_len_mismatch:
        print(f"[WARN] len_bin vs n_chars mismatch detected: {warn_len_mismatch} item(s)")
    if bad_c:
        print("[WARN] remaining bad cluster_id idx:", bad_c[:10])
    if mid_l:
        print("[WARN] remaining len_bin='mid' idx:", mid_l[:10])

    sample = [
        (it.get("id"), it.get("cluster_id"), it.get("diff_bin"), it.get("len_bin"),
         it.get("n_chars"), it.get("prompt_hash", "")[:8])
        for it in after.get("items", [])[:5]
    ]
    print("[SAMPLE first5]", sample)

if __name__ == "__main__":
    main()