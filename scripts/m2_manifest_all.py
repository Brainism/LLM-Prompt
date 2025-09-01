from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def length_bin_from_text(text: str):
    n = len((text or "").split())
    if n <= 120:
        return "short"
    if n <= 360:
        return "medium"
    return "long"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="data/raw/metadata/meta.jsonl")
    ap.add_argument("--prompts", default="data/raw/prompts/prompts.jsonl")
    ap.add_argument("--manifest_out", default="data/manifest/split_manifest_main.json")
    args = ap.parse_args()

    meta_path = Path(args.meta)
    prompts_path = Path(args.prompts)
    out_path = Path(args.manifest_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    id2prompt = {}
    if prompts_path.exists():
        for r in load_jsonl(prompts_path):
            id2prompt[str(r.get("id", ""))] = r

    rows = []
    if meta_path.exists():
        meta = load_jsonl(meta_path)
        for m in meta:
            rid = str(m.get("id", ""))
            domain = m.get("domain") or id2prompt.get(rid, {}).get("domain") or ""
            lang = m.get("lang") or id2prompt.get(rid, {}).get("lang") or ""
            diff = m.get("diff_bin") or id2prompt.get(rid, {}).get("diff_bin") or ""
            cid = m.get("cluster_id") or id2prompt.get(rid, {}).get("cluster_id") or rid
            lenbin = m.get("len_bin")
            if not lenbin:
                inp = id2prompt.get(rid, {}).get("input", "")
                lenbin = length_bin_from_text(inp)
            rows.append(
                {
                    "id": rid,
                    "domain": domain,
                    "lang": lang,
                    "len_bin": lenbin,
                    "diff_bin": diff,
                    "cluster_id": cid,
                }
            )
    else:
        for p in load_jsonl(prompts_path):
            rid = str(p.get("id", ""))
            inp = p.get("input", "")
            rows.append(
                {
                    "id": rid,
                    "domain": p.get("domain", ""),
                    "lang": p.get("lang", ""),
                    "len_bin": length_bin_from_text(inp),
                    "diff_bin": p.get("diff_bin", ""),
                    "cluster_id": p.get("cluster_id", rid),
                }
            )

    rows.sort(key=lambda x: x["id"])
    out_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[manifest_all] wrote {out_path}  selected={len(rows)}")


if __name__ == "__main__":
    main()
