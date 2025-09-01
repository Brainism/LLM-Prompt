from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def truthy(v: str) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "y", "yes")


def read_text_any(p: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949", "mbcs", "euc-kr", "latin1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_bytes().decode("utf-8", errors="ignore")


def load_needs_json_ids(csv_path: Path) -> tuple[set[str], dict[str, list[str]]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"apply-from csv not found: {csv_path}")

    ids: set[str] = set()
    ref_tags_map: dict[str, list[str]] = {}

    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8-sig")))
    for r in rows:
        pid = (r.get("id") or "").strip()
        if not pid:
            continue

        if truthy(r.get("needs_json")):
            ids.add(pid)

        try:
            ref = r.get("reference") or ""
            ref_obj = json.loads(ref) if ref.strip().startswith("{") else None
            if isinstance(ref_obj, dict) and isinstance(ref_obj.get("tags"), list):
                ref_tags_map[pid] = [
                    str(t).strip() for t in ref_obj["tags"] if str(t).strip()
                ]
        except Exception:
            pass

    return ids, ref_tags_map


CODEFENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)\s*```", re.IGNORECASE)


def extract_json_block(s: str) -> dict | list | None:
    if not isinstance(s, str) or not s.strip():
        return None

    m = CODEFENCE_RE.search(s)
    if m:
        txt = m.group(1).strip()
        for cand in _json_candidates(txt):
            obj = _try_json(cand)
            if obj is not None:
                return obj

    for cand in _json_candidates(s):
        obj = _try_json(cand)
        if obj is not None:
            return obj

    return None


def _json_candidates(s: str) -> list[str]:
    s = s.strip()
    cands: list[str] = []
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        cands.append(s[i : j + 1])
    i2, j2 = s.find("["), s.rfind("]")
    if i2 != -1 and j2 != -1 and j2 > i2:
        cands.append(s[i2 : j2 + 1])
    return cands


def _try_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def normalize_title_tags(
    obj,
    *,
    min_tags: int = 2,
    max_tags: int | None = 5,
    ref_tags: list[str] | None = None,
) -> dict | None:
    if not isinstance(obj, dict):
        return None
    if "title" not in obj or "tags" not in obj:
        return None

    title = str(obj.get("title", "")).strip()

    tags = obj.get("tags", [])
    if isinstance(tags, list):
        tags = [str(t).strip() for t in tags if str(t).strip()]
    else:
        tag_str = str(tags).strip()
        tags = [tag_str] if tag_str else []

    if max_tags is not None and max_tags > 0:
        tags = tags[:max_tags]

    if len(tags) < min_tags:
        if ref_tags:
            need = min_tags - len(tags)
            add = [t for t in ref_tags if t not in tags][:need]
            tags.extend(add)
        while len(tags) < min_tags:
            tags.append(tags[0] if tags else "tag")

    return {"title": title, "tags": tags}


def process_jsonl_file(
    in_path: Path,
    out_path: Path,
    target_ids: set[str],
    ref_tags_map: dict[str, list[str]],
    max_tags: int,
) -> tuple[int, int, int]:
    text = read_text_any(in_path)
    lines = [ln for ln in text.splitlines() if ln.strip()]

    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = patched = skipped = 0

    with out_path.open("w", encoding="utf-8") as fw:
        for s in lines:
            try:
                rec = json.loads(s)
            except Exception:
                fw.write(s + "\n")
                skipped += 1
                continue

            total += 1
            pid = str(rec.get("id", "")).strip()
            if pid and pid in target_ids:
                out_text = rec.get("output", "")
                obj = extract_json_block(out_text)
                ref_tags = ref_tags_map.get(pid)
                norm = (
                    normalize_title_tags(
                        obj, min_tags=2, max_tags=max_tags, ref_tags=ref_tags
                    )
                    if obj is not None
                    else None
                )
                if norm is not None:
                    rec["output"] = json.dumps(
                        norm, ensure_ascii=False, separators=(",", ":")
                    )
                    patched += 1
                else:
                    skipped += 1
            else:
                skipped += 1

            fw.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return total, patched, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--apply-from",
        type=Path,
        required=True,
        help="prompts.csv (needs_json 플래그 소스)",
    )
    ap.add_argument(
        "--raw-in", type=Path, default=Path("results") / "raw", help="입력 jsonl 폴더"
    )
    ap.add_argument(
        "--raw-out",
        type=Path,
        default=Path("results") / "raw_patched",
        help="출력 jsonl 폴더",
    )
    ap.add_argument("--glob", default="*.jsonl", help="대상 파일 패턴 (기본: *.jsonl)")
    ap.add_argument(
        "--max-tags",
        type=int,
        default=5,
        help="tags 최대 개수(기본 5, 0이면 제한 없음)",
    )
    args = ap.parse_args()

    target_ids, ref_tags_map = load_needs_json_ids(args.apply_from)
    if not target_ids:
        print(f"[warn] needs_json=1 대상 id가 없습니다. ({args.apply_from})")

    in_dir = args.raw_in
    out_dir = args.raw_out
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_dir.glob(args.glob))
    if not files:
        print(f"[warn] 입력 파일이 없습니다: {in_dir}\\{args.glob}")
        return

    grand_total = grand_patched = grand_skipped = 0
    for fp in files:
        out_fp = out_dir / fp.name
        total, patched, skipped = process_jsonl_file(
            fp, out_fp, target_ids, ref_tags_map, max_tags=args.max_tags
        )
        grand_total += total
        grand_patched += patched
        grand_skipped += skipped
        print(
            f"[ok] {fp.name} -> {out_fp.name}  (records={total}, patched={patched}, skipped={skipped})"
        )

    print(
        f"[summary] files={len(files)}  total={grand_total}  patched={grand_patched}  skipped={grand_skipped}"
    )
    print(
        "[hint] 다음을 실행하여 재집계하세요:\n"
        f"  python code/compliance_check.py --apply-from prompts/prompts.csv --raw-dir {out_dir} "
        f"--limit-chars 1000 --bullets-min-n 3 --limit-items-json 5 --forbid-terms docs/forbid_terms.txt\n"
        "  python code/make_compliance_snapshot.py"
    )


if __name__ == "__main__":
    main()
