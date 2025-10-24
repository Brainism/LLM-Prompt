import os, csv, json, argparse, hashlib, re
from pathlib import Path
from collections import Counter

HDR = ["id","input","reference","domain","lang","len_bin","diff_bin","license","cluster_id"]

def ensure_hdr(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(HDR)

def hash8(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]

def guess_lang(text: str, fallback="en"):
    return "ko" if re.search(r"[가-힣]", text or "") else fallback

def len_bin_from_text(text: str, lang: str):
    n = len(text or "")
    if lang == "ko":
        return "short" if n<=120 else ("medium" if n<=360 else "long")
    else:
        return "short" if n<=600 else ("medium" if n<=1500 else "long")

def diff_bin_from_text(text: str):
    score = 0
    if re.search(r"\{.*\}|\[.*\]|</?\w+>|def |class |SELECT |INSERT |UPDATE |```", text or "", flags=re.I|re.S):
        score += 2
    if re.search(r"\d{2,}", text or ""):
        score += 1
    return "hard" if score>=2 else ("medium" if score==1 else "easy")

def sanitize_cluster_id(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\-]", "_", s or "")
    return s[:64] or "GEN"

def read_manifest(p: Path):
    data = json.loads(p.read_text(encoding="utf-8"))
    rows=[]
    for it in data.get("items", []):
        rows.append({
            "id": it["id"],
            "input": it["input"],
            "reference": it["reference"],
            "domain": it.get("domain","general"),
            "lang": it["lang"],
            "len_bin": it["len_bin"],
            "diff_bin": it["diff_bin"],
            "license": it.get("license","CC-BY-4.0"),
            "cluster_id": sanitize_cluster_id(it.get("cluster_id") or f'{it.get("domain","general")}_{it["lang"]}_{it["len_bin"]}_{it["diff_bin"]}')
        })
    return rows

def _norm(s):
    return (s or "").strip().lstrip("\ufeff").lower()

def read_prompts_csv(p: Path, default_license="CC-BY-4.0"):
    with p.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit(f"[ERR] CSV 헤더가 없습니다: {p}")
        norm_map = { _norm(h): h for h in r.fieldnames }
        need_min = ["id","input","reference","lang","len_bin","diff_bin"]
        missing = [k for k in need_min if k not in norm_map]
        if missing:
            raise SystemExit(f"[ERR] prompts CSV 필수 헤더 부족: {missing} / 실제={r.fieldnames}")
        rows=[]
        for row in r:
            g = {k: row.get(norm_map[k], "") for k in need_min}
            dom = row.get(norm_map.get("domain",""), "") if "domain" in norm_map else ""
            lic = row.get(norm_map.get("license",""), "") if "license" in norm_map else ""
            cid = row.get(norm_map.get("cluster_id",""), "") if "cluster_id" in norm_map else ""

            if not dom: dom = "general"
            if not g["lang"]: g["lang"] = guess_lang(g["input"])
            if not g["len_bin"]: g["len_bin"] = len_bin_from_text(g["input"], g["lang"])
            if not g["diff_bin"]: g["diff_bin"] = diff_bin_from_text(g["input"])
            if not lic: lic = default_license
            if not cid: cid = sanitize_cluster_id(f'{dom}_{g["lang"]}_{g["len_bin"]}_{g["diff_bin"]}')

            rows.append({
                "id": g["id"],
                "input": g["input"],
                "reference": g["reference"],
                "domain": dom,
                "lang": g["lang"],
                "len_bin": g["len_bin"],
                "diff_bin": g["diff_bin"],
                "license": lic,
                "cluster_id": cid
            })
    final=[]; seen=set()
    for r in rows:
        base = r["id"] or f"{r['lang']}_{hash8(r['input'])}"
        rid = base; i=1
        while rid in seen:
            i+=1; rid=f"{base}_{i}"
        r["id"]=rid; seen.add(rid); final.append(r)
    return final

def scan_sources(root: Path, default_license="CC-BY-4.0"):
    rows=[]
    for p in root.rglob("*.jsonl"):
        lang_hint = "ko" if "ko" in p.parts else ("en" if "en" in p.parts else "en")
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            j = json.loads(line)
            inp = (j.get("input") or "").strip(); ref = (j.get("reference") or "").strip()
            if not inp or not ref: continue
            lang = j.get("lang") or guess_lang(inp, lang_hint)
            lb   = j.get("len_bin") or len_bin_from_text(inp, lang)
            db   = j.get("diff_bin") or diff_bin_from_text(inp)
            dom  = j.get("domain") or "general"
            lic  = j.get("license") or default_license
            cid  = sanitize_cluster_id(j.get("cluster_id") or f"{dom}_{lang}_{lb}_{db}")
            rid  = j.get("id") or f"{lang}_{hash8(inp)}"
            rows.append({"id":rid,"input":inp,"reference":ref,"domain":dom,"lang":lang,"len_bin":lb,"diff_bin":db,"license":lic,"cluster_id":cid})
    for p in root.rglob("*.in.txt"):
        stem = p.stem[:-3] if p.stem.endswith(".in") else p.stem
        refp = p.parent / f"{stem}.ref.txt"
        if not refp.exists(): continue
        inp = p.read_text(encoding="utf-8").strip()
        ref = refp.read_text(encoding="utf-8").strip()
        if not inp or not ref: continue
        lang_hint = "ko" if "ko" in p.parts else ("en" if "en" in p.parts else "en")
        lang = guess_lang(inp, lang_hint)
        lb   = len_bin_from_text(inp, lang)
        db   = diff_bin_from_text(inp)
        dom  = p.parent.name if p.parent.name not in ("ko","en") else "general"
        lic  = default_license
        cid  = sanitize_cluster_id(f"{dom}_{lang}_{lb}_{db}")
        rid  = f"{lang}_{hash8(inp)}"
        rows.append({"id":rid,"input":inp,"reference":ref,"domain":dom,"lang":lang,"len_bin":lb,"diff_bin":db,"license":lic,"cluster_id":cid})
    uniq=[]; seen=set()
    for r in rows:
        key=(r["input"], r["reference"])
        if key in seen: continue
        seen.add(key); uniq.append(r)
    return uniq

def write_candidates(path: Path, rows):
    ensure_hdr(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=HDR)
        w.writeheader(); w.writerows(rows)
    print(f"[OK] wrote {path} (n={len(rows)})")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--from-manifest")
    ap.add_argument("--from-prompts")
    ap.add_argument("--scan")
    ap.add_argument("--out", default="data/candidates.csv")
    ap.add_argument("--license", default="CC-BY-4.0")
    args=ap.parse_args()

    if args.from_manifest and Path(args.from_manifest).exists():
        rows = read_manifest(Path(args.from_manifest))
    elif args.from_prompts and Path(args.from_prompts).exists():
        rows = read_prompts_csv(Path(args.from_prompts), default_license=args.license)
    elif args.scan and Path(args.scan).exists():
        rows = scan_sources(Path(args.scan), default_license=args.license)
    else:
        raise SystemExit("[ERR] 유효한 데이터 소스를 찾지 못했습니다. --from-manifest / --from-prompts / --scan 중 하나를 지정하세요.")

    write_candidates(Path(args.out), rows)

if __name__ == "__main__":
    main()