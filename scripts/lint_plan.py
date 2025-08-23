from pathlib import Path
import re, sys, json

REQ = {
  "study_scope.md": [
    r"## 1\. Domains", r"## 2\. Languages", r"## 3\. Length bins",
    r"## 4\. Difficulty bins", r"## 5\. Target sample size", r"## 6\. Sources"
  ],
  "analysis_plan.md": [
    r"## A\. Hypotheses", r"## B\. Primary / Secondary metrics", r"## C\. Data & Splits",
    r"## D\. Statistical plan", r"## E\. Logging schema", r"## F\. Stopping / Gate"
  ]
}

def check(md: Path, patterns):
    txt = md.read_text(encoding="utf-8") if md.exists() else ""
    missing = [p for p in patterns if re.search(p, txt) is None]
    return {"file": str(md), "exists": md.exists(), "missing_sections": missing}

def main():
    docs = Path("docs")
    results = []
    for fname, pats in REQ.items():
        results.append(check(docs / fname, pats))
    ok = all(r["exists"] and not r["missing_sections"] for r in results)
    print(json.dumps({"ok": ok, "details": results}, ensure_ascii=False, indent=2))
    if not ok: sys.exit(1)

if __name__ == "__main__":
    main()