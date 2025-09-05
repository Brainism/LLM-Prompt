import json, argparse, os, math

def is_number(x):
    try:
        return isinstance(x, (int, float)) and not math.isnan(float(x))
    except Exception:
        return False

def process(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        items = data["items"]
        print(f"[SKIP] already wrapped: {path} (items={len(items)})")
        return

    if isinstance(data, list):
        items = data
        ok = sum(1 for r in items if isinstance(r, dict) and is_number(r.get("base")) and is_number(r.get("instr")))
        wrapped = {"items": items}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(wrapped, f, ensure_ascii=False, indent=2)
        print(f"[OK] wrapped: {path} (items={len(items)}, valid_pairs={ok})")
        return

    raise RuntimeError(f"Unsupported JSON shape in {path}: expected list or object-with-items")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="+", required=True)
    args = ap.parse_args()
    for p in args.paths:
        if not os.path.exists(p):
            print(f"[WARN] not found: {p}")
            continue
        process(p)

if __name__ == "__main__":
    main()