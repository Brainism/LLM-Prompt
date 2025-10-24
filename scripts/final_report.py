import csv, json, pathlib

QUANT = pathlib.Path("results/quantitative")
stats_boot = QUANT / "stats_bootstrap.csv"
p_q = QUANT / "p_q_values.csv"
simple = QUANT / "stats_simple_after_retry.csv"
out = QUANT / "final_report.csv"

boot_map = {}
if stats_boot.exists():
    with stats_boot.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            m = row.get("metric") or row.get("metric")
            boot_map[m] = row

pq_map = {}
if p_q.exists():
    with p_q.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            pq_map[row['metric']] = row

simple_map = {}
if simple.exists():
    with simple.open(encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            simple_map[row['metric']] = row

metrics = ["bleu_sacre","rouge","chrf"]
rows = []
for m in metrics:
    boot = boot_map.get(m, {})
    s = simple_map.get(m, {})
    pq = pq_map.get(m, {})
    mean_base = s.get("mean_base") or boot.get("mean_base") or ""
    mean_instr = s.get("mean_instr") or boot.get("mean_instr") or ""
    delta = s.get("delta") or boot.get("delta") or ""
    ci_lo = boot.get("ci_lo") or boot.get("ci_lo") or ""
    ci_hi = boot.get("ci_hi") or boot.get("ci_hi") or ""
    p = pq.get("p") or ""
    q = pq.get("q_bh") or ""
    n = s.get("n") or boot.get("n") or ""
    rows.append({
        "metric": m, "n": n, "mean_base": mean_base, "mean_instr": mean_instr,
        "delta": delta, "ci_lo": ci_lo, "ci_hi": ci_hi, "p": p, "q": q
    })

out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["metric","n","mean_base","mean_instr","delta","ci_lo","ci_hi","p","q"])
    w.writeheader()
    for r in rows:
        w.writerow(r)

print("[FINAL REPORT] summary:")
for r in rows:
    metric = r['metric']
    print(f"- {metric}: n={r['n']}, mean_base={r['mean_base']}, mean_instr={r['mean_instr']}, delta={r['delta']}, CI=[{r['ci_lo']},{r['ci_hi']}], p={r['p']}, q={r['q']}")

print()
print(f"[OK] final_csv -> {out}")