import json
from jsonschema import validate, Draft7Validator

schema = json.load(open("schema/split_manifest_main.schema.json", encoding="utf-8"))
manifest = json.load(open("data/manifest/split_manifest_main.json", encoding="utf-8"))

errors = sorted(Draft7Validator(schema).iter_errors(manifest), key=lambda e: e.path)
if errors:
    for e in errors:
        print("❌", "/".join(map(str, e.path)) or "(root)", "-", e.message)
    raise SystemExit(1)
print("✅ manifest OK")
