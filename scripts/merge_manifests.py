# scripts/merge_manifests.py
import json
import os

IN_FILES = [
    r"data\manifest\split_manifest_v0.4_migrated.json",
    r"data\manifest\split_manifest_v0.4_medium_hard.json",
    r"data\manifest\split_manifest_v0.4_long_hard.json",
]
OUT_FILE = r"data\manifest\split_manifest_v0.4_full.json"


def load_items(path):
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict) and "items" in doc:
        return doc["items"]
    raise ValueError(f"Unsupported format: {path}")


def main():
    all_items = []
    for p in IN_FILES:
        items = load_items(p)
        all_items.extend(items)
    full = {"items": all_items}

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)
    print(f"[OK] merged -> {OUT_FILE} (items={len(all_items)})")


if __name__ == "__main__":
    main()
