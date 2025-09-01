import csv
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prompts_csv = ROOT / "prompts" / "prompts.csv"
out_dir = ROOT / "data" / "manifest"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "split_manifest.json"


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def len_bin(n_chars: int) -> str:
    if n_chars < 100:
        return "short"
    if n_chars < 300:
        return "medium"
    return "long"


def detect_lang_from_id(pid: str) -> str:
    up = pid.upper()
    if up.startswith("EN_"):
        return "en"
    if up.startswith("KO_"):
        return "ko"
    return "ko"


def cluster_id_from_id(pid: str) -> str:
    up = pid.upper()
    m = re.match(r"^([A-Z]+)[\-_]?(\d+)$", up)
    if m:
        prefix, num = m.group(1), m.group(2).zfill(4)
        return f"{prefix}_CLUSTER_{num}"
    m = re.match(r"^([A-Z]+)[\-_](\d+)$", up)
    if m:
        prefix, num = m.group(1), m.group(2).zfill(4)
        return f"{prefix}_CLUSTER_{num}"
    sanitized = re.sub(r"[^A-Z0-9]+", "_", up).strip("_")
    return f"CLUSTER_{sanitized}"


def read_prompts(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        id_keys = ["id", "ID", "Id"]
        text_keys = ["input", "text", "prompt"]
        dom_keys = ["domain", "scenario"]
        for row in reader:
            pid = next((row[k] for k in id_keys if k in row and row[k]), "").strip()
            text = next((row[k] for k in text_keys if k in row and row[k]), "").strip()
            domain = (
                next((row[k] for k in dom_keys if k in row and row[k]), "").strip()
                or "general"
            )
            if not pid or not text:
                continue
            yield {"id": pid, "text": text, "domain": domain}


def sort_key(pid: str):
    m = re.match(r"^([A-Za-z]+)[\-_]?(\d+)$", pid)
    if m:
        return (m.group(1).upper(), int(m.group(2)))
    return ("ZZZ", pid)


def main():
    items = []
    rows = list(read_prompts(prompts_csv))
    if not rows:
        raise SystemExit(f"[fail] no valid rows in {prompts_csv}")

    for r in rows:
        pid = r["id"]
        text = r["text"]
        it = {
            "id": pid,
            "domain": r["domain"] or "general",
            "lang": detect_lang_from_id(pid),
            "len_bin": len_bin(len(text)),
            "cluster_id": cluster_id_from_id(pid),
            "prompt_hash": sha256_text(text),
            "n_chars": len(text),
            "license": "unknown",
        }
        items.append(it)

    items.sort(key=lambda x: sort_key(x["id"]))

    if out_path.exists():
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup = out_path.with_suffix(f".{ts}.bak.json")
        out_path.replace(backup)
        print(f"[info] existing manifest backed up -> {backup.name}")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[ok] manifest -> {out_path} (count={len(items)})")


if __name__ == "__main__":
    main()
