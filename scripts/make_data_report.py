import os
import json
import csv
import datetime
from statistics import mean

QDIR = "results/quantitative"
RDIR = "results/raw/v2"
DDIR = "docs"

MD_PATH = os.path.join(DDIR, "data_report.md")
HTML_PATH = os.path.join(DDIR, "data_report.html")

def safe_load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_items_metric(name):
    path = os.path.join(QDIR, f"{name}.json")
    obj = safe_load_json(path)
    items = []
    if obj is None:
        return items
    if isinstance(obj, dict) and isinstance(obj.get("items"), list):
        src = obj["items"]
    elif isinstance(obj, list):
        src = obj
    else:
        return items

    for x in src:
        if not isinstance(x, dict):
            continue
        _id = x.get("id")
        if _id is None:
            continue
        try:
            base = float(x.get("base", 0) or 0)
        except Exception:
            base = 0.0
        try:
            instr = float(x.get("instr", 0) or 0)
        except Exception:
            instr = 0.0
        items.append({"id": str(_id), "base": base, "instr": instr})
    return items

def read_stats_summary():
    path = os.path.join(QDIR, "stats_summary.v2.csv")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        m = (r.get("metric") or "").strip().lower()
        if m:
            out[m] = r
    return out

def read_latency_summary():
    path = os.path.join(QDIR, "latency_summary.v2.csv")
    if not os.path.exists(path):
        return None, None, []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = [row for row in reader]
    return header, rows[:5], rows

def read_pass_delta():
    path = os.path.join(QDIR, "pass_delta.v2.csv")
    if not os.path.exists(path):
        return {"same": None, "diff": None, "only_base": None, "only_cvd": None}
    same = diff = only_base = only_cvd = 0
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            b = r.get("base_pass")
            c = r.get("cvd_pass")
            d = r.get("delta")
            def to_bool(x):
                s = str(x).strip().lower()
                return s in ("1","true","t","y","yes","pass")
            if b == "" and c == "" and d == "":
                continue
            if (b != "" and c != ""):
                if to_bool(b) == to_bool(c):
                    same += 1
                else:
                    diff += 1
            elif b != "" and c == "":
                only_base += 1
            elif b == "" and c != "":
                only_cvd += 1
    return {"same": same, "diff": diff, "only_base": only_base, "only_cvd": only_cvd}

def md_table(header, rows):
    h = "| " + " | ".join(header) + " |\n"
    sep = "| " + " | ".join(["---"] * len(header)) + " |\n"
    body = ""
    for r in rows:
        body += "| " + " | ".join(str(x) for x in r) + " |\n"
    return h + sep + body

def fmtf(x, nd=3):
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)

def main():
    os.makedirs(DDIR, exist_ok=True)

    bleu_items = load_items_metric("bleu_sacre")
    n_pairs = len(bleu_items) if bleu_items else None
    prompts_path = os.path.join("prompts", "main.csv")
    if n_pairs is None and os.path.exists(prompts_path):
        with open(prompts_path, "r", encoding="utf-8") as f:
            n_pairs = sum(1 for _ in csv.DictReader(f))
    n_pairs = n_pairs or "n/a"

    metrics_summary = {}
    for name in ("bleu_sacre", "chrf", "rouge"):
        items = load_items_metric(name)
        if items:
            base_mean = mean([x["base"] for x in items])
            instr_mean = mean([x["instr"] for x in items])
            metrics_summary[name] = {
                "mean_base": base_mean,
                "mean_instr": instr_mean,
                "delta": instr_mean - base_mean,
                "n": len(items),
            }
        else:
            metrics_summary[name] = {"mean_base":"n/a","mean_instr":"n/a","delta":"n/a","n":"n/a"}

    provider = "ollama"
    model = "gemma:7b"
    seed = 42

    stats = read_stats_summary()
    def statrow(mkey, label):
        r = stats.get(mkey, {})
        return [
            label,
            r.get("n", "n/a"),
            fmtf(r.get("mean_base")),
            fmtf(r.get("mean_instr")),
            fmtf(r.get("delta")),
            fmtf(r.get("delta_%")),
            fmtf(r.get("d")),
            fmtf(r.get("CI95_low")),
            fmtf(r.get("CI95_high")),
            fmtf(r.get("p")),
            fmtf(r.get("q")),
        ]

    stats_table = md_table(
        ["metric","n","mean_base","mean_instr","Δ","Δ%","d","CI95_low","CI95_high","p","q"],
        [
            statrow("bleu_sacre","BLEU"),
            statrow("rouge","ROUGE-L"),
            statrow("chrf","chrF"),
        ]
    )

    lat_header, lat_preview, _lat_all = read_latency_summary()
    lat_md = ""
    if lat_header and lat_preview:
        lat_md = "### Latency (preview)\n" + md_table(lat_header, lat_preview)

    pass_delta = read_pass_delta()
    comp_md = ""
    if any(v is not None for v in pass_delta.values()):
        comp_md = (
            "### Compliance delta (pass)\n"
            f"- same: {pass_delta.get('same')}, diff: {pass_delta.get('diff')}, "
            f"only_base: {pass_delta.get('only_base')}, only_cvd: {pass_delta.get('only_cvd')}\n"
        )

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    md = []
    md.append(f"# Data Report — v2 run\n")
    md.append(f"- Generated: {now}\n")
    md.append(f"- Pairs (n): {n_pairs}\n")
    md.append(f"- Provider / Model / Seed: {provider} / {model} / {seed}\n")
    md.append("\n## Aggregate means (per-id)\n")
    md.append(md_table(
        ["metric","mean_base","mean_instr","Δ","n(items)"],
        [
            ["BLEU",  fmtf(metrics_summary["bleu_sacre"]["mean_base"]), fmtf(metrics_summary["bleu_sacre"]["mean_instr"]), fmtf(metrics_summary["bleu_sacre"]["delta"]), metrics_summary["bleu_sacre"]["n"]],
            ["ROUGE-L", fmtf(metrics_summary["rouge"]["mean_base"]), fmtf(metrics_summary["rouge"]["mean_instr"]), fmtf(metrics_summary["rouge"]["delta"]), metrics_summary["rouge"]["n"]],
            ["chrF",  fmtf(metrics_summary["chrf"]["mean_base"]), fmtf(metrics_summary["chrf"]["mean_instr"]), fmtf(metrics_summary["chrf"]["delta"]), metrics_summary["chrf"]["n"]],
        ]
    ))
    md.append("\n## Paired statistics\n")
    md.append(stats_table)
    if lat_md:
        md.append("\n")
        md.append(lat_md)
    if comp_md:
        md.append("\n")
        md.append(comp_md)
    md.append("\n---\n")
    md.append("**Notes**\n")
    md.append("- Aggregate means above are computed from per-id files (`bleu_sacre.json`, `chrf.json`, `rouge.json`) to avoid folder contamination.\n")
    md.append("- Paired statistics are taken from `results/quantitative/stats_summary.v2.csv` (bootstrap CI, Wilcoxon, BH-FDR).\n")
    md.append("- For detailed cases, open `figs/error_board.html` (Top/Bottom ΔBLEU examples).\n")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"[OK] wrote {MD_PATH}")

    html = f"""<!doctype html>
<meta charset="utf-8">
<title>Data Report — v2 run</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, Segoe UI, Arial; margin: 24px; line-height: 1.45; }}
  h1, h2, h3 {{ margin: 16px 0 8px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
  th {{ background: #f7f7f7; }}
  code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
</style>
<article>
{''.join('<p>'+line+'</p>' if line and not line.startswith('|') and not line.startswith('- ') and not line.startswith('#') else line for line in "\n".join(md).splitlines())}
</article>
"""
    os.makedirs(DDIR, exist_ok=True)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] wrote {HTML_PATH}")

if __name__ == "__main__":
    main()