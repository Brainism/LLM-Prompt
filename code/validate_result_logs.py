import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schema" / "result_log.schema.json"
DEFAULT_RAWDIR = ROOT / "results" / "raw"


def iter_jsonl_lines(fp: Path):
    with fp.open("r", encoding="utf-8-sig", errors="replace") as f:
        for ln_no, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            yield ln_no, s


def main():
    ap = argparse.ArgumentParser(
        description="Validate result JSONL logs against schema"
    )
    ap.add_argument(
        "--schema", type=Path, default=DEFAULT_SCHEMA, help="path to JSON schema file"
    )
    ap.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAWDIR,
        help="directory containing *.jsonl logs",
    )
    ap.add_argument(
        "--glob", default="*.jsonl", help="filename glob pattern (default: *.jsonl)"
    )
    ap.add_argument(
        "--max-errors", type=int, default=50, help="maximum number of errors to print"
    )
    ap.add_argument(
        "--require",
        nargs="*",
        default=[],
        help="extra required keys (e.g., mode provider model)",
    )
    args = ap.parse_args()

    if not args.schema.exists():
        raise FileNotFoundError(f"?ㅽ궎留덈? 李얠쓣 ???놁뒿?덈떎: {args.schema}")
    if not args.raw_dir.exists():
        raise FileNotFoundError(f"raw 濡쒓렇 ?대뜑媛 ?놁뒿?덈떎: {args.raw_dir}")

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    files = sorted(args.raw_dir.glob(args.glob))
    if not files:
        print("[WARN] 寃곌낵 濡쒓렇媛 ?놁뒿?덈떎.")
        sys.exit(0)

    total_records = 0
    ok_records = 0
    errors = []

    for fp in files:
        for ln_no, s in iter_jsonl_lines(fp):
            total_records += 1
            try:
                rec = json.loads(s)
            except Exception as e:
                errors.append((fp.name, ln_no, "(parse)", f"JSON ?뚯떛 ?ㅽ뙣: {e}"))
                continue

            v_errs = list(validator.iter_errors(rec))
            for k in args.require:
                if k not in rec:
                    v_errs.append(
                        ("__extra__", [k], f"Extra required key missing: '{k}'")
                    )

            if v_errs:
                for e in v_errs:
                    if isinstance(e, tuple):
                        _, path_list, msg = e
                        path_str = (
                            "/".join(map(str, path_list)) if path_list else "(root)"
                        )
                        errors.append((fp.name, ln_no, path_str, msg))
                    else:
                        path_str = (
                            "/".join(map(str, getattr(e, "path", []))) or "(root)"
                        )
                        errors.append(
                            (fp.name, ln_no, path_str, getattr(e, "message", str(e)))
                        )
            else:
                ok_records += 1

    print(
        f"[SUMMARY] files={len(files)}  records={total_records}  ok={ok_records}  errors={len(errors)}"
    )
    if errors:
        show_n = min(args.max_errors, len(errors))
        print(f"[DETAILS] showing first {show_n} errors:")
        for f, ln, path, msg in errors[:show_n]:
            print(f"- {f}:{ln} :: {path} :: {msg}")
        sys.exit(1)
    else:
        print("??result logs OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
