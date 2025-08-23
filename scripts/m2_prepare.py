from __future__ import annotations
import argparse, csv, json, math, os, re, sys
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple, Optional, Set

LEN_SHORT_MAX = 120
LEN_MED_MAX   = 360
MIN_BIN_SHARE = 0.15
EMAIL_RE  = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE  = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\d{2,4}[-.\s]?){2,3}\d{2,4}")
RRN_RE    = re.compile(r"\d{6}-\d{7}")

def ensure_dirs():
    Path("data/raw/prompts").mkdir(parents=True, exist_ok=True)
    Path("data/raw/references").mkdir(parents=True, exist_ok=True)
    Path("data/raw/metadata").mkdir(parents=True, exist_ok=True)
    Path("data/manifest").mkdir(parents=True, exist_ok=True)
    Path("rules").mkdir(parents=True, exist_ok=True)
    Path("docs").mkdir(parents=True, exist_ok=True)

def load_forbidden_terms(path: Path) -> Set[str]:
    if not path.exists(): return set()
    terms=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        s=line.strip()
        if not s or s.startswith("#"): continue
        terms.append(s.lower())
    return set(terms)

def read_txt_folder(folder: Path) -> Dict[str,str]:
    out={}
    for f in folder.glob("*.txt"):
        out[f.stem]=f.read_text(encoding="utf-8").strip()
    return out

def read_jsonl(path: Path) -> List[Dict[str,Any]]:
    data=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        data.append(json.loads(line))
    return data

def read_metadata(folder: Path) -> Dict[str,Dict[str,Any]]:
    meta={}
    for f in folder.glob("*.jsonl"):
        for obj in read_jsonl(f):
            id_=str(obj.get("id") or obj.get("item_id") or obj.get("uid"))
            if id_:
                meta.setdefault(id_,{}).update(obj)
    for f in folder.glob("*.csv"):
        with f.open(encoding="utf-8", newline="") as fp:
            for row in csv.DictReader(fp):
                id_=str(row.get("id") or row.get("item_id") or row.get("uid") or "").strip()
                if not id_: continue
                r={k:v for k,v in row.items() if k!="id"}
                meta.setdefault(id_,{}).update(r)
    return meta

def length_bin(text: str) -> str:
    n=len(text.split())
    if n<=LEN_SHORT_MAX: return "short"
    if n<=LEN_MED_MAX:  return "medium"
    return "long"

def infer_lang(text: str, fallback="ko")->str:
    if re.search(r"[가-힣]", text): return "ko"
    return fallback

def jaccard_shingles(a: str, b: str, k: int = 5) -> float:
    def shingles(s):
        s=re.sub(r"\s+"," ", s.strip())
        return {s[i:i+k] for i in range(max(len(s)-k+1,1))}
    A,B=shingles(a), shingles(b)
    inter=len(A & B); union=len(A | B)
    return inter/union if union else 0.0

def detect_pii_or_forbidden(text: str, forbid: Set[str])->List[str]:
    issues=[]
    if EMAIL_RE.search(text): issues.append("email")
    if PHONE_RE.search(text): issues.append("phone")
    if RRN_RE.search(text):   issues.append("rrn")
    low=text.lower()
    for t in forbid:
        if t and t in low:
            issues.append(f"forbidden:{t}")
    return issues

def load_sources():
    raw=Path("data/raw"); prompts,refs={},{}
    prompts.update(read_txt_folder(raw/"prompts"))
    refs.update(read_txt_folder(raw/"references"))
    for f in (raw/"prompts").glob("*.jsonl"):
        for obj in read_jsonl(f):
            id_=str(obj.get("id") or obj.get("item_id") or obj.get("uid"))
            inp=obj.get("input") or obj.get("prompt") or obj.get("source")
            if id_ and isinstance(inp,str): prompts[id_]=inp
    for f in (raw/"references").glob("*.jsonl"):
        for obj in read_jsonl(f):
            id_=str(obj.get("id") or obj.get("item_id") or obj.get("uid"))
            ref=obj.get("reference") or obj.get("target") or obj.get("label")
            if id_ and isinstance(ref,str): refs[id_]=ref
    meta=read_metadata(raw/"metadata")
    return prompts, refs, meta

def build_manifest(target_n:int, min_sim:float, forbid:Set[str]):
    prompts, refs, meta=load_sources()
    ids=sorted(set(prompts)|set(refs)|set(meta))
    if not ids: return [], {"note":"no_raw_data","counts":{}}
    rows=[]
    for id_ in ids:
        inp=prompts.get(id_,""); ref=refs.get(id_,""); m=meta.get(id_,{})
        domain=m.get("domain") or "summarization"
        lang=m.get("lang") or infer_lang(inp or ref or "", fallback="ko")
        diff=m.get("diff_bin") or "normal"
        cluster=m.get("cluster_id") or (id_.split("__")[0] if "__" in id_ else id_)
        lb=m.get("len_bin") or length_bin(inp or ref or "")
        rows.append({"id":id_,"domain":str(domain),"lang":str(lang),"len_bin":str(lb),
                     "diff_bin":str(diff),"cluster_id":str(cluster),
                     "has_prompt":bool(inp),"has_reference":bool(ref),
                     "input":inp,"reference":ref})
    flagged=[]
    for r in rows:
        issues=[]
        issues+=detect_pii_or_forbidden(r["input"] or "", forbid)
        issues+=detect_pii_or_forbidden(r["reference"] or "", forbid)
        r["issues"]=issues
        if issues: flagged.append(r["id"])
    rows=[r for r in rows if not r["issues"]]
    kept, removed, seen=[],[],[]
    for r in rows:
        txt=(r["input"] or "").strip()
        if not txt: kept.append(r); continue
        is_dup=False
        for s in seen:
            if jaccard_shingles(txt,s)>=min_sim:
                removed.append(r["id"]); is_dup=True; break
        if not is_dup:
            seen.append(txt); kept.append(r)
    final=kept
    if target_n>0 and len(kept)>target_n:
        buckets=defaultdict(list)
        for r in kept:
            key=(r["domain"],r["lang"],r["len_bin"],r["diff_bin"])
            buckets[key].append(r)
        final=[]; keys=list(buckets.keys()); idx=0
        while len(final)<target_n:
            bkey=keys[idx%len(keys)]
            if buckets[bkey]: final.append(buckets[bkey].pop())
            idx+=1
    counts={
        "raw_total": len(ids),
        "flagged_pii_or_forbid": len(set(flagged)),
        "removed_near_duplicates": len(set(removed)),
        "kept_after_filters": len(kept),
        "selected_for_manifest": len(final),
        "by_len_bin": Counter([r["len_bin"] for r in final]),
        "by_diff_bin": Counter([r["diff_bin"] for r in final]),
        "by_domain": Counter([r["domain"] for r in final]),
        "by_lang": Counter([r["lang"] for r in final]),
    }
    manifest=[{k:r[k] for k in ("id","domain","lang","len_bin","diff_bin","cluster_id")} for r in final]
    return manifest, counts

def write_manifest(manifest, out_path:Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

def write_report(counts, out_md:Path, target_n:int):
    out_md.parent.mkdir(parents=True, exist_ok=True)
    def fmt_counter(c:Counter):
        if not c: return "-"
        total=sum(c.values()) or 1
        lines=["| key | n | share |","|---|---:|---:|"]
        for k,v in sorted(c.items(), key=lambda x:(-x[1], str(x[0]))):
            lines.append(f"| {k} | {v} | {100*v/total:.1f}% |")
        return "\n".join(lines)
    lines=["# Data Report (M2)",""]
    if counts.get("note")=="no_raw_data":
        lines.append("> **No raw data found.** Put sources under `data/raw/` and rerun.")
    else:
        lines+=[
          f"- Raw total ids: **{counts['raw_total']}**",
          f"- Flagged (PII/forbidden): **{counts['flagged_pii_or_forbid']}**",
          f"- Removed near-duplicates: **{counts['removed_near_duplicates']}**",
          f"- Kept after filters: **{counts['kept_after_filters']}**",
          f"- Selected for manifest (target={target_n}): **{counts['selected_for_manifest']}**",
          "", "## Length bins", fmt_counter(counts["by_len_bin"]), "",
          "## Difficulty bins", fmt_counter(counts["by_diff_bin"]), "",
          "## Domains", fmt_counter(counts["by_domain"]), "",
          "## Languages", fmt_counter(counts["by_lang"]), ""
        ]
        def chk(counter:Counter, label:str):
            total=sum(counter.values()); 
            if not total: return
            warns=[]
            for k,v in counter.items():
                share=v/total
                if share<MIN_BIN_SHARE:
                    warns.append(f"{label} '{k}' share {share:.2%} < {MIN_BIN_SHARE:.0%}")
            if warns:
                lines.append("## Warnings")
                for w in warns: lines.append(f"- ⚠️ {w}")
        chk(counts["by_len_bin"], "len_bin")
        chk(counts["by_diff_bin"], "diff_bin")
    out_md.write_text("\n".join(lines), encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--target_n", type=int, default=50)
    ap.add_argument("--min_similarity", type=float, default=0.90)
    ap.add_argument("--manifest_out", default="data/manifest/split_manifest.json")
    ap.add_argument("--report_out", default="docs/data_report.md")
    ap.add_argument("--forbidden_terms", default="rules/forbidden_terms.txt")
    args=ap.parse_args()
    ensure_dirs()
    forbid=load_forbidden_terms(Path(args.forbidden_terms))
    manifest, counts=build_manifest(args.target_n, args.min_similarity, forbid)
    write_manifest(manifest, Path(args.manifest_out))
    write_report(counts, Path(args.report_out), args.target_n)
    if not manifest:
        print("[m2] No raw data found. Created skeleton under data/raw/. Add sources and rerun.", file=sys.stderr)
        sys.exit(2)
    print(f"[m2] wrote {args.manifest_out} and {args.report_out}. selected={len(manifest)}")

if __name__=="__main__":
    main()