import json
import os
import re
import sys
import tempfile

RX = re.compile(r"^[A-Z0-9_-]+$")


def sanitize_cluster_id(val):
    s = str(val if val is not None else "")
    s = s.upper()
    s = re.sub(r"[^A-Z0-9_-]", "_", s)
    if not s:
        s = "CLUSTER"
    return s


def normalize_diff_bin(val):
    if val is None:
        return None
    v = str(val).strip().lower()
    if v in {"mid", "med", "middle"}:
        return "medium"
    if v in {"easy", "medium", "hard"}:
        return v
    return None


def main(path):
    abspath = os.path.abspath(path)
    print("[PATH]", abspath)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    cfix = dfix = 0
    for it in items:
        if "cluster_id" in it:
            old = it["cluster_id"]
            new = sanitize_cluster_id(old)
            if new != old:
                it["cluster_id"] = new
                cfix += 1

        db = it.get("diff_bin", None)
        newdb = normalize_diff_bin(db)
        if newdb != db:
            it["diff_bin"] = newdb
            dfix += 1

        if not RX.fullmatch(it.get("cluster_id", "")):
            it["cluster_id"] = sanitize_cluster_id(it.get("cluster_id", ""))
            cfix += 1

    ddir, fname = os.path.split(path)
    fd, tmp = tempfile.mkstemp(prefix=fname + ".", dir=ddir or ".")
    os.close(fd)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

    with open(path, "r", encoding="utf-8") as f:
        after = json.load(f)
    bad_c = [
        i
        for i, it in enumerate(after.get("items", []))
        if not RX.fullmatch(str(it.get("cluster_id", "")))
    ]
    bad_d = [
        i for i, it in enumerate(after.get("items", [])) if it.get("diff_bin") == "mid"
    ]

    print(f"[OK] wrote: {path}")
    print(f"[FIX] cluster_id: {cfix}, diff_bin: {dfix}, total_items={len(items)}")
    if bad_c or bad_d:
        print(
            "[WARN] remaining issues:",
            f"bad_cluster_ids={bad_c[:10]}",
            f"bad_diff_bin_mid={bad_d[:10]}",
        )
    else:
        for i, it in enumerate(after.get("items", [])[:5]):
            print("SAMPLE", i, it.get("cluster_id"), it.get("diff_bin"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python scripts/fix_manifest_fields_v2.py data\\manifest\\split_manifest_main.json"
        )
        sys.exit(2)
    main(sys.argv[1])
