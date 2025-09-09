import csv, json, argparse, random, re
from collections import Counter, defaultdict
from pathlib import Path

LANGS = ["ko","en"]
LENS  = ["short","medium","long"]
DIFFS = ["easy","medium","hard"]
CELL_KEYS = [(a,b,c) for a in LANGS for b in LENS for c in DIFFS]

def sanitize_cluster_id(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\\-]", "_", (s or "GEN"))
    return s[:64]

def load_candidates(path):
    rows=[]
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        need = {"id","input","reference","domain","lang","len_bin","diff_bin","license","cluster_id"}
        if not {"id","input","reference","lang","len_bin","diff_bin"}.issubset(set(r.fieldnames or [])):
            raise SystemExit(f"[ERR] data/candidates.csv header mismatch: {r.fieldnames}")
        for row in r:
            rec = {
                "id": (row.get("id") or "").strip(),
                "input": (row.get("input") or "").strip(),
                "reference": (row.get("reference") or "").strip(),
                "domain": (row.get("domain") or "general").strip(),
                "lang": (row.get("lang") or "").strip(),
                "len_bin": (row.get("len_bin") or "").strip(),
                "diff_bin": (row.get("diff_bin") or "").strip(),
                "license": (row.get("license") or "CC-BY-4.0").strip(),
                "cluster_id": sanitize_cluster_id(row.get("cluster_id") or "")
            }
            rows.append(rec)
    filtered=[]
    for r in rows:
        if not r["input"] or not r["reference"]:
            continue
        if r["lang"] not in LANGS:
            r["lang"] = "ko" if re.search(r"[가-힣]", r["input"]) else "en"
        if r["len_bin"] not in LENS:
            n = len(r["input"])
            if r["lang"]=="ko":
                r["len_bin"] = "short" if n<=120 else ("medium" if n<=360 else "long")
            else:
                r["len_bin"] = "short" if n<=600 else ("medium" if n<=1500 else "long")
        if r["diff_bin"] not in DIFFS:
            s = r["input"]
            score = 0
            if re.search(r"\{.*\}|\[.*\]|</?\w+>|def |class |SELECT |INSERT |UPDATE |```", s, flags=re.I|re.S):
                score += 2
            if re.search(r"\d{2,}", s):
                score += 1
            r["diff_bin"] = "hard" if score>=2 else ("medium" if score==1 else "easy")
        if not r["cluster_id"]:
            r["cluster_id"] = sanitize_cluster_id(f"{r['domain']}_{r['lang']}_{r['len_bin']}_{r['diff_bin']}")
        if not r["id"]:
            base = f"{r['lang']}_{hash(r['input']) & 0xffffffff:08x}"
            r["id"] = base
        filtered.append(r)
    ids = [x["id"] for x in filtered]
    dup = [k for k,c in Counter(ids).items() if c>1]
    if dup:
        seen=set(); out=[]
        for r in filtered:
            base=r["id"]; i=1; new=base
            while new in seen:
                i+=1; new=f"{base}_{i}"
            r["id"]=new; seen.add(new); out.append(r)
        filtered = out
    return filtered

def cell_key(r):
    return (r["lang"], r["len_bin"], r["diff_bin"])

def cell_distance(a, b):
    lang_cost = 0 if a[0]==b[0] else 10
    len_cost = abs(LENS.index(a[1]) - LENS.index(b[1]))
    diff_cost = abs(DIFFS.index(a[2]) - DIFFS.index(b[2]))
    return lang_cost + len_cost + diff_cost

def make_plan(total_n, avail_counter):
    base = total_n // len(CELL_KEYS)
    rem = total_n - base*len(CELL_KEYS)
    sorted_cells = sorted(CELL_KEYS, key=lambda k: (-avail_counter.get(k,0), k))
    plus_one = set(sorted_cells[:rem])
    plan={}
    for k in CELL_KEYS:
        plan[k] = base + (1 if k in plus_one else 0)
    return plan

def pick_with_fallback(rows, plan, seed):
    rng = random.Random(seed)
    bycell=defaultdict(list)
    for r in rows:
        bycell[cell_key(r)].append(r)
    for k in bycell:
        rng.shuffle(bycell[k])

    chosen=[]
    pools = {k:list(v) for k,v in bycell.items()}
    shortages = {}
    for cell,need in plan.items():
        avail = len(pools.get(cell,[]))
        take = min(avail, need)
        if take>0:
            for _ in range(take):
                chosen.append(pools[cell].pop())
        if take < need:
            shortages[cell] = need - take

    for cell,need in list(shortages.items()):
        if need<=0: continue
        cand=[]
        for other, pool in pools.items():
            if not pool: continue
            dist = cell_distance(cell, other)
            for item in pool:
                cand.append((dist, other, item))
        cand.sort(key=lambda x:(x[0], x[1]))
        taken=0
        used = []
        for entry in cand:
            if taken>=need: break
            dist, other, item = entry
            try:
                pools[other].remove(item)
            except ValueError:
                continue
            chosen.append(item); taken+=1
        shortages[cell] -= taken
        if shortages[cell] <= 0:
            del shortages[cell]

    synthetic_count = 0
    for cell,need in shortages.items():
        all_items = [r for v in bycell.values() for r in v] + chosen
        if not all_items:
            raise SystemExit("[ERR] No candidates at all to duplicate for synthetic fill.")
        all_items_sorted = sorted(all_items, key=lambda it: cell_distance(cell_key(it), cell))
        for i in range(need):
            src = all_items_sorted[i % len(all_items_sorted)]
            synthetic_count += 1
            new = dict(src)
            new_id = f"{src['id']}_SYN{synthetic_count}"
            new['id'] = new_id
            new['cluster_id'] = sanitize_cluster_id(new.get('cluster_id',"") + "_SYN")
            chosen.append(new)

    if len(chosen) < sum(plan.values()):
        needed = sum(plan.values()) - len(chosen)
        remaining = [item for plist in pools.values() for item in plist]
        rng.shuffle(remaining)
        take = min(len(remaining), needed)
        for i in range(take):
            chosen.append(remaining[i])
        if len(chosen) < sum(plan.values()):
            need2 = sum(plan.values()) - len(chosen)
            for i in range(need2):
                src = chosen[i % len(chosen)]
                new = dict(src)
                new_id = f"{src['id']}_SYND{i+1}"
                new['id'] = new_id
                new['cluster_id'] = sanitize_cluster_id(new['cluster_id'] + "_SYND")
                chosen.append(new)

    desired = sum(plan.values())
    if len(chosen) > desired:
        rng.shuffle(chosen)
        chosen = chosen[:desired]

    return chosen

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args=ap.parse_args()

    rows = load_candidates(args.candidates)
    if not rows:
        raise SystemExit("[ERR] No valid candidates found in data/candidates.csv")

    avail = Counter([cell_key(r) for r in rows])
    plan = make_plan(args.n, avail)

    print("C:\\Project\\LLM\\scripts 디렉터리")
    print("[DIAG] availability per cell (non-zero only):")
    for k,v in sorted(avail.items()):
        print(" ", k, ":", v)

    zeros = [k for k in CELL_KEYS if avail.get(k,0)==0]
    if zeros:
        print("[WARN] some cells have zero candidates:", zeros)

    chosen = pick_with_fallback(rows, plan, args.seed)

    out = {"items":[
        {
          "id": r["id"],
          "input": r["input"],
          "reference": r["reference"],
          "domain": r.get("domain","general"),
          "lang": r["lang"],
          "len_bin": r["len_bin"],
          "diff_bin": r["diff_bin"],
          "cluster_id": r["cluster_id"],
          "license": r.get("license","CC-BY-4.0")
        } for r in chosen
    ]}

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out,"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[OK] manifest -> {args.out} (n={len(out['items'])})")
    from collections import Counter as C
    grp = C((it['lang'], it['len_bin'], it['diff_bin']) for it in out['items'])
    print("[OUT_DIST] lang×len×diff:", dict(grp))

if __name__=="__main__":
    main()