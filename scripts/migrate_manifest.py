import json, hashlib, os, sys

SRC = r"data\manifest\split_manifest_main.json"
DST = r"data\manifest\split_manifest_v0.4_migrated.json"

LEN_BINS = {
    "short": (1, 70),
    "medium": (71, 160),
    "long": (161, 10_000_000)
}

def detect_len_bin(n):
    for k, (lo, hi) in LEN_BINS.items():
        if lo <= n <= hi:
            return k
    return "long"

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and "items" in raw:
        items = raw["items"]
    else:
        print("Unsupported manifest format.")
        sys.exit(1)

    migrated = {"items": []}

    for it in items:
        it = dict(it)

        it.setdefault("input", it.get("input", it.get("prompt", "")))
        if not it["input"]:
            it["input"] = f"[PLACEHOLDER INPUT for {it.get('id','(no-id)')}]"

        it.setdefault("reference", it.get("reference", ""))
        if not it["reference"]:
            it["reference"] = "[PLACEHOLDER REFERENCE]"

        it.setdefault("lang", "ko")

        if "diff_bin" not in it:
            it["diff_bin"] = None

        n_chars = len(it["input"])
        it["n_chars"] = n_chars
        it["len_bin"] = detect_len_bin(n_chars)

        it["prompt_hash"] = sha256_hex(it["input"].strip())

        it.setdefault("domain", "general")
        it.setdefault("cluster_id", "EX_CLUSTER_AUTO")
        it.setdefault("license", "unknown")

        migrated["items"].append(it)

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(migrated, f, ensure_ascii=False, indent=2)

    print(f"[OK] migrated -> {DST} (items={len(migrated['items'])})")

if __name__ == "__main__":
    main()