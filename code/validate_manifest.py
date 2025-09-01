from __future__ import annotations
import sys
import json
from pathlib import Path

from jsonschema import Draft7Validator

def main(manifest_path: str, schema_path: str) -> None:
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for e in errors:
            loc = "/".join(map(str, e.path)) or "(root)"
            print(f"[ERR] {loc} - {e.message}")
        sys.exit(1)
    print("[OK] manifest OK")

if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "data/manifest/split_manifest_main.json"
    s = sys.argv[2] if len(sys.argv) > 2 else "schema/split_manifest_main.schema.json"
    main(m, s)