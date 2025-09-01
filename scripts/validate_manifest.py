import argparse
import json
import os
import sys
from typing import Any, Dict, List

from jsonschema import Draft7Validator


def _resolve_path(path_str: str, script_dir: str) -> str:
    if not path_str:
        return path_str
    if os.path.isabs(path_str):
        return path_str
    cand = os.path.abspath(path_str)
    if os.path.exists(cand):
        return cand
    cand = os.path.abspath(os.path.join(script_dir, path_str))
    return cand


def _filesize(path: str) -> str:
    try:
        n = os.path.getsize(path)
        return f"{n} B"
    except Exception:
        return "?"


def _json_pointer_from_error_path(path_parts) -> str:
    parts = [str(p) for p in path_parts]
    return "/".join(parts) if parts else "(root)"


def _preview_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "cluster_id": item.get("cluster_id"),
        "lang": item.get("lang"),
        "len_bin": item.get("len_bin"),
        "diff_bin": item.get("diff_bin"),
        "n_chars": item.get("n_chars"),
    }


def _print_sample_items(items: List[Dict[str, Any]], k: int):
    sample = items[:k]
    print("[DEBUG] sample items (trimmed):")
    for i, it in enumerate(sample):
        print(f"  #{i}: {_preview_item(it)}")


def _warn_duplicates(items: List[Dict[str, Any]]):
    ids = [it.get("id") for it in items if isinstance(it, dict)]
    seen, dups = set(), []
    for x in ids:
        if x in seen:
            dups.append(x)
        else:
            seen.add(x)
    if dups:
        uniq = sorted(set(dups))
        print(
            f"[WARN] duplicate id(s) detected (count={len(uniq)}): {uniq[:10]}{' ...' if len(uniq)>10 else ''}"
        )


def _warn_lenbin_nchars_presence(items: List[Dict[str, Any]]):
    missing_nc = []
    missing_lb = []
    mismatch = []
    for i, it in enumerate(items):
        lb = it.get("len_bin")
        nc = it.get("n_chars")
        if lb is not None and nc is None:
            missing_nc.append(i)
        if nc is not None and lb is None:
            missing_lb.append(i)
        if isinstance(nc, int) and isinstance(lb, str):
            if lb == "short" and not (1 <= nc <= 70):
                mismatch.append(i)
            elif lb == "medium" and not (71 <= nc <= 160):
                mismatch.append(i)
            elif lb == "long" and not (nc >= 161):
                mismatch.append(i)
    if missing_nc:
        print(
            f"[WARN] len_bin 존재하지만 n_chars 누락 idx (예시 10개): {missing_nc[:10]}"
        )
    if missing_lb:
        print(
            f"[WARN] n_chars 존재하지만 len_bin 누락 idx (예시 10개): {missing_lb[:10]}"
        )
    if mismatch:
        print(
            f"[WARN] len_bin ↔ n_chars 범위 불일치 의심 idx (예시 10개): {mismatch[:10]}"
        )


def validate_manifest(
    manifest_path: str, schema_path: str, *, max_errors: int = 100, show_sample: int = 5
) -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("[DEBUG] CWD =", os.getcwd())

    manifest_path = _resolve_path(manifest_path, script_dir)
    schema_path = _resolve_path(schema_path, script_dir)

    print(
        "[DEBUG] manifest_path =",
        os.path.abspath(manifest_path),
        f"({ _filesize(manifest_path) })",
    )
    print(
        "[DEBUG] schema_path   =",
        os.path.abspath(schema_path),
        f"({ _filesize(schema_path) })",
    )

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except FileNotFoundError:
        print(f"[FATAL] schema file not found: {schema_path}")
        return 2
    except json.JSONDecodeError as e:
        print(f"[FATAL] invalid JSON in schema: {schema_path}: {e}")
        return 2

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[FATAL] manifest file not found: {manifest_path}")
        return 2
    except json.JSONDecodeError as e:
        print(f"[FATAL] invalid JSON in manifest: {manifest_path}: {e}")
        return 2

    items = data.get("items", [])
    if not isinstance(items, list):
        print("[FATAL] manifest.items must be a list")
        return 2
    print(f"[DEBUG] n_items = {len(items)}")
    if show_sample > 0:
        _print_sample_items(items, show_sample)

    v = Draft7Validator(schema)
    errors = sorted(v.iter_errors(data), key=lambda e: list(e.path))

    if not errors:
        print("[OK] schema validation passed.")
        _warn_duplicates(items)
        _warn_lenbin_nchars_presence(items)
        return 0

    print("[ERR] validation failed:")
    for e in errors[:max_errors]:
        path_str = _json_pointer_from_error_path(e.path)
        print(f" - at [{path_str}]: {e.message}")
        try:
            parts = list(e.path)
            if len(parts) >= 2 and parts[0] == "items" and isinstance(parts[1], int):
                idx = parts[1]
                if 0 <= idx < len(items):
                    print(f"   > item[{idx}] preview: {_preview_item(items[idx])}")
        except Exception:
            pass

    more = len(errors) - max_errors
    if more > 0:
        print(f"[NOTE] ... {more} more errors not shown")

    print(f"[FAIL] {len(errors)} validation error(s).")
    print(
        "[HINT] 흔한 원인: len_bin='mid' 미정규화, cluster_id 비허용문자, id 패턴 불일치, n_chars 범위/누락 등."
    )
    print(
        "[HINT] 자동 보정 도구: python scripts\\fix_manifest_fields_v3.py data\\manifest\\split_manifest_main.json --inplace --add-prompt-hash --auto-len-bin"
    )
    return 1


def main_legacy(manifest_path: str, schema_path: str):
    code = validate_manifest(manifest_path, schema_path, max_errors=50, show_sample=5)
    if code == 0:
        print("[OK] manifest validated!")
        sys.exit(0)
    elif code == 1:
        sys.exit(2)
    else:
        sys.exit(code)


def cli():
    ap = argparse.ArgumentParser(
        description="Validate manifest JSON against the schema (with helpful debug prints)."
    )
    ap.add_argument(
        "--manifest",
        default=r"data\manifest\split_manifest_main.json",
        help="Path to manifest JSON (default: data\\manifest\\split_manifest_main.json)",
    )
    ap.add_argument(
        "--schema",
        default=r"schema\split_manifest_main.schema.json",
        help="Path to JSON schema (default: schema\\split_manifest_main.schema.json)",
    )
    ap.add_argument(
        "--max-errors",
        type=int,
        default=100,
        help="Max errors to display (default: 100)",
    )
    ap.add_argument(
        "--show-sample",
        type=int,
        default=5,
        help="How many items to preview (default: 5)",
    )
    ap.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy exit codes/messages similar to the minimal version.",
    )
    args = ap.parse_args()

    code = validate_manifest(
        args.manifest,
        args.schema,
        max_errors=args.max_errors,
        show_sample=args.show_sample,
    )
    if args.legacy:
        if code == 0:
            print("[OK] manifest validated!")
            sys.exit(0)
        elif code == 1:
            sys.exit(2)
        else:
            sys.exit(code)
    else:
        sys.exit(code)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[0].endswith("validate_manifest.py"):
        main_legacy(sys.argv[1], sys.argv[2])
    else:
        cli()
