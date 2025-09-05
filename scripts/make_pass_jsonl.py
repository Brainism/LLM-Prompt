from __future__ import annotations
import argparse, json
from pathlib import Path

def read_text_any(p: Path) -> str:
    for enc in ("utf-8-sig","utf-8","cp949","mbcs","euc-kr","latin1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_bytes().decode("utf-8", errors="ignore")

def load_forbid_terms(path: Path):
    if not path or not path.exists():
        return []
    txt = read_text_any(path)
    return [t.strip() for t in txt.splitlines() if t.strip()]

class FallbackVerifier:
    def __init__(self, forbid_path: Path|None, schema_path: Path|None):
        self.terms = load_forbid_terms(forbid_path) if forbid_path else []
        self.schema = None
        self.validator = None
        if schema_path and schema_path.exists():
            try:
                import jsonschema
                from jsonschema import Draft7Validator
                self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
                self.validator = Draft7Validator(self.schema)
            except Exception:
                self.validator = None

    def check(self, text: str):
        reasons = []
        low = (text or "").lower()
        for t in self.terms:
            if t.lower() in low:
                reasons.append(f"forbidden:{t}")
        if self.validator is not None:
            try:
                obj = json.loads(text)
            except Exception:
                reasons.append("not_json")
            else:
                errs = list(self.validator.iter_errors(obj))
                if errs:
                    reasons.append("jsonschema_invalid")
        elif self.schema is not None:
            reasons.append("jsonschema_missing")
        return (len(reasons) == 0), reasons

def main():
    ap = argparse.ArgumentParser(description="Add 'pass' boolean to JSONL by verifying output text.")
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--forbid", required=False)
    ap.add_argument("--schema", required=False)
    args = ap.parse_args()

    vin = FallbackVerifier(Path(args.forbid) if args.forbid else None,
                           Path(args.schema) if args.schema else None)

    src = Path(args.inputs)
    dst = Path(args.out)
    dst.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with src.open("r", encoding="utf-8-sig", errors="replace") as f, \
         dst.open("w", encoding="utf-8") as g:
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            try:
                o = json.loads(s)
            except Exception:
                continue
            ok, _reasons = vin.check(o.get("output","") or "")
            o["pass"] = bool(ok)
            g.write(json.dumps(o, ensure_ascii=False) + "\n")
            n += 1
    print(f"[OK] wrote {dst} lines={n}")

if __name__ == "__main__":
    main()