import json
import sys
import argparse
from pathlib import Path
from jsonschema import Draft7Validator, exceptions as jsonschema_exceptions

ROOT   = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "result_log.schema.json"
RAWDIR = ROOT / "results" / "raw"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-errors", type=int, default=50, help="maximum number of errors to print")
    ap.add_argument("--require", nargs="*", default=[], help="extra required keys (e.g., mode provider)")
    args = ap.parse_args()

    if not SCHEMA.exists():
        raise FileNotFoundError(f"스키마를 찾을 수 없습니다: {SCHEMA}")
    if not RAWDIR.exists():
        raise FileNotFoundError(f"raw 로그 폴더가 없습니다: {RAWDIR}")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    files = sorted(RAWDIR.glob("*.jsonl"))
    if not files:
        print("[WARN] results/raw 에 jsonl이 없습니다.")
        sys.exit(0)

    total = 0
    ok = 0
    errs = []

    for fp in files:
        text = fp.read_text(encoding="utf-8")
        for ln_no, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if not s:
                continue
            total += 1
            try:
                rec = json.loads(s)
            except Exception as e:
                errs.append((fp.name, ln_no, "(parse)", f"JSON 파싱 실패: {e}"))
                continue

            v_errors = list(validator.iter_errors(rec))
            for k in args.require:
                if k not in rec:
                    v_errors.append(jsonschema_exceptions.ValidationError(
                        f"Extra required key missing: '{k}'", path=[k]
                    ))

            if v_errors:
                for e in v_errors:
                    path = "/".join(map(str, e.path)) or "(root)"
                    errs.append((fp.name, ln_no, path, e.message))
            else:
                ok += 1

    print(f"[SUMMARY] files={len(files)}  records={total}  ok={ok}  errors={len(errs)}")
    if errs:
        print(f"[DETAILS] showing first {min(args.max_errors, len(errs))} errors:")
        for f, ln, path, msg in errs[:args.max_errors]:
            print(f"- {f}:{ln} :: {path} :: {msg}")
        sys.exit(1)
    else:
        print("✅ result logs OK")

if __name__ == "__main__":
    main()