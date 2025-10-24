import json
from pathlib import Path
import sys

MANIFEST = Path("data/manifest/split_manifest_main.json")

def load_manifest(p: Path):
    if not p.exists():
        print(f"[ERR] manifest not found: {p}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERR] failed to read/parse manifest: {e}", file=sys.stderr)
        sys.exit(3)
    if "items" not in data or not isinstance(data["items"], list):
        print("[ERR] manifest.items missing or not a list", file=sys.stderr)
        sys.exit(4)
    return data

def add_n_chars(data):
    for it in data["items"]:
        try:
            n = it.get("n_chars", None)
            if n in (None, "", 0):
                it["n_chars"] = len(it.get("input","") or "")
            else:
                it["n_chars"] = int(n)
        except Exception:
            it["n_chars"] = len(it.get("input","") or "")
    return data

def write_manifest(p: Path, data):
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[ERR] failed to write manifest: {e}", file=sys.stderr)
        sys.exit(5)

def main():
    data = load_manifest(MANIFEST)
    data = add_n_chars(data)
    write_manifest(MANIFEST, data)
    print(f"[OK] n_chars added/updated in {MANIFEST} (n={len(data.get('items',[]))})")

if __name__ == "__main__":
    main()