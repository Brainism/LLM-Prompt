import json, math, csv
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

def _to_float(x):
    try: return float(x)
    except: return float("nan")

def _extract_score(v):
    if isinstance(v,(int,float)): return float(v)
    if isinstance(v,dict):
        for k in ("score","value","f1","f","metric","val"):
            if k in v: return _to_float(v[k])
    return float("nan")

def _infer_metric_key(per):
    pri=("rougeL_f","bleu4","rougeL","bleu","score","value","f1","f")
    if not per: raise ValueError("per_item empty")
    s=per[0]
    for k in pri:
        if k in s and isinstance(s[k],(int,float)): return k
    for k,v in s.items():
        if k not in ("id","prompt_id","prompt_type","mode") and isinstance(v,(int,float)):
            return k
    raise ValueError("no numeric key")

def load_pairs_any(path: Path) -> Tuple[List[str], np.ndarray, np.ndarray]:
    d = json.loads(path.read_text(encoding="utf-8"))
    ids: List[str]=[]; G: List[float]=[]; I: List[float]=[]

    if isinstance(d,dict) and "items" in d and isinstance(d["items"],list) and d["items"]:
        for idx,it in enumerate(d["items"]):
            pid=str(it.get("id") or it.get("prompt_id") or idx)
            if "general" in it and "instructed" in it:
                g=_extract_score(it["general"]); i=_extract_score(it["instructed"])
            else:
                m=it.get("modes",{})
                g=_extract_score(m.get("general")); i=_extract_score(m.get("instructed"))
            if not (math.isnan(g) or math.isnan(i)): ids.append(pid); G.append(g); I.append(i)

    elif isinstance(d,dict) and ("general" in d) and ("instructed" in d or "instruct" in d):
        inst_key = "instructed" if "instructed" in d else "instruct"
        def as_map(x):
            if isinstance(x,list):
                m={}
                for j,xx in enumerate(x):
                    pid=str(xx.get("id",j)); m[pid]=_extract_score(xx.get("score", xx.get("value", xx)))
                return m
            if isinstance(x,dict):
                return {str(k):_extract_score(v) for k,v in x.items()}
            return {}
        gmap=as_map(d["general"]); imap=as_map(d[inst_key])
        common=sorted(set(gmap)&set(imap))
        ids=common; G=[gmap[k] for k in common]; I=[imap[k] for k in common]

    elif isinstance(d,dict) and "per_item" in d and isinstance(d["per_item"],list):
        per=d["per_item"]; mkey=_infer_metric_key(per)
        gmap:Dict[str,float]={}; imap:Dict[str,float]={}
        for idx,x in enumerate(per):
            pid=str(x.get("id") or x.get("prompt_id") or idx)
            mode=str(x.get("prompt_type") or x.get("mode") or "").lower()
            val=x.get(mkey)
            if val is None: continue
            if mode.startswith("gen"): gmap[pid]=_to_float(val)
            elif mode.startswith("instr"): imap[pid]=_to_float(val)
        common=sorted(set(gmap)&set(imap))
        ids=common; G=[gmap[k] for k in common]; I=[imap[k] for k in common]

    elif isinstance(d,list) and d and isinstance(d[0],dict) and (("general" in d[0]) or ("instructed" in d[0]) or ("instruct" in d[0])):
        for idx,x in enumerate(d):
            g=_extract_score(x.get("general")); i=_extract_score(x.get("instructed", x.get("instruct")))
            if not (math.isnan(g) or math.isnan(i)):
                ids.append(str(x.get("id",idx))); G.append(g); I.append(i)

    elif isinstance(d,list) and d and isinstance(d[0],dict) and ("score" in d[0]) and ("system" in d[0] or "model" in d[0]):
        gmap:Dict[str,float]={}; imap:Dict[str,float]={}
        for idx,x in enumerate(d):
            pid=str(x.get("id",idx)); sysname=str(x.get("system", x.get("model",""))).lower()
            sc=_extract_score(x.get("score"))
            if sysname.startswith("gen"): gmap[pid]=sc
            elif sysname.startswith("instr"): imap[pid]=sc
        common=sorted(set(gmap)&set(imap))
        ids=common; G=[gmap[k] for k in common]; I=[imap[k] for k in common]
    else:
        return [], np.array([]), np.array([])

    G=np.array(G,float); I=np.array(I,float)
    mask=~(np.isnan(G)|np.isnan(I))
    return ids, G[mask], I[mask]

def dump(metric_path: str, out_csv: str):
    ids,g,i = load_pairs_any(Path(metric_path))
    diff = i-g
    out = Path(out_csv); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id","general","instructed","diff"])
        for pid,gv,iv,dv in zip(ids,g,i,diff): w.writerow([pid, f"{gv:.6f}", f"{iv:.6f}", f"{dv:.6f}"])
    print(f"[OK] wrote {out} ({len(diff)} rows).  meanΔ={diff.mean():.6f}")

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--metric", required=True)
    ap.add_argument("--out", required=True)
    a=ap.parse_args()
    dump(a.metric, a.out)