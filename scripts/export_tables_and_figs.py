import os
import json
import csv
import math

QDIR = "results/quantitative"
TDIR = "tables"
FDIR = "figs"

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dirs():
    os.makedirs(TDIR, exist_ok=True)
    os.makedirs(FDIR, exist_ok=True)

def write_csv(path: str, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)

def gen_tables():
    rouge_path = os.path.join(QDIR, "rouge_scores.v2.json")
    bleu_chrf_path = os.path.join(QDIR, "bleu_chrf.v2.json")

    rouge = load_json(rouge_path) if os.path.exists(rouge_path) else {}
    bleu_chrf = load_json(bleu_chrf_path) if os.path.exists(bleu_chrf_path) else {}

    metrics_rows = [
        ["rougeL_f1_mean", rouge.get("rougeL_f1_mean"), rouge.get("n")],
        ["BLEU_mean",      bleu_chrf.get("BLEU"),      bleu_chrf.get("n")],
        ["chrF_mean",      bleu_chrf.get("chrF"),      bleu_chrf.get("n")],
    ]
    write_csv(os.path.join(TDIR, "metrics.csv"), ["metric", "value", "n"], metrics_rows)

    stats_csv = os.path.join(QDIR, "stats_summary.v2.csv")
    if os.path.exists(stats_csv):
        header, stats_rows = None, []
        with open(stats_csv, "r", encoding="utf-8") as f:
            for i, row in enumerate(csv.reader(f)):
                if i == 0:
                    header = row
                else:
                    stats_rows.append(row)
        if header:
            write_csv(os.path.join(TDIR, "stats.csv"), header, stats_rows)

    lat_path = os.path.join(QDIR, "latency_summary.v2.csv")
    if os.path.exists(lat_path):
        lhead, lat_rows = None, []
        with open(lat_path, "r", encoding="utf-8") as f:
            for i, row in enumerate(csv.reader(f)):
                if i == 0:
                    lhead = row
                else:
                    lat_rows.append(row)
        if lhead:
            write_csv(os.path.join(TDIR, "latency.csv"), lhead, lat_rows)

    print("[OK] wrote tables/*")

def gen_error_board(topk: int = 10):
    def _items(name: str):
        path = os.path.join(QDIR, f"{name}.json")
        if not os.path.exists(path):
            return []

        obj = load_json(path)

        if isinstance(obj, dict) and isinstance(obj.get("items"), list):
            items = obj["items"]
        elif isinstance(obj, list):
            items = obj
        else:
            raise ValueError(
                f"Unsupported JSON shape in {path}: expected dict-with-items or list"
            )

        out = []
        for x in items:
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
            out.append({"id": str(_id), "base": base, "instr": instr})
        return out

    b = _items("bleu_sacre")
    c = _items("chrf")
    r = _items("rouge")

    d = {}
    for L, tag in ((b, "bleu"), (c, "chrf"), (r, "rouge")):
        for x in L:
            d.setdefault(x["id"], {}).update({
                f"{tag}_base":  x["base"],
                f"{tag}_instr": x["instr"],
            })

    rows = []
    for k, v in d.items():
        rows.append({
            "id": k,
            "bleu_delta":  v.get("bleu_instr", 0)  - v.get("bleu_base", 0),
            "chrf_delta":  v.get("chrf_instr", 0)  - v.get("chrf_base", 0),
            "rouge_delta": v.get("rouge_instr", 0) - v.get("rouge_base", 0),
            **v
        })

    up   = sorted(rows, key=lambda x: x["bleu_delta"], reverse=True)[:topk]
    down = sorted(rows, key=lambda x: x["bleu_delta"])[:topk]

    def fmt(v):
        try:
            fv = float(v)
            if math.isnan(fv):
                return "nan"
            return f"{fv:.3f}"
        except Exception:
            return str(v)

    def row_html(x):
        return (
            "<tr>"
            f"<td>{x['id']}</td>"
            f"<td>{fmt(x.get('bleu_base', 0))}</td>"
            f"<td>{fmt(x.get('bleu_instr', 0))}</td>"
            f"<td><b>{fmt(x.get('bleu_delta', 0))}</b></td>"
            f"<td>{fmt(x.get('chrf_base', 0))}</td>"
            f"<td>{fmt(x.get('chrf_instr', 0))}</td>"
            f"<td>{fmt(x.get('chrf_delta', 0))}</td>"
            f"<td>{fmt(x.get('rouge_base', 0))}</td>"
            f"<td>{fmt(x.get('rouge_instr', 0))}</td>"
            f"<td>{fmt(x.get('rouge_delta', 0))}</td>"
            "</tr>"
        )

    html = f"""<!doctype html><meta charset="utf-8">
<title>Error/Delta Board</title>
<style>
 body {{ font-family: ui-sans-serif, system-ui, Segoe UI, Arial; margin: 20px; }}
 table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
 th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: right; }}
 th {{ background:#fafafa; }}
 td:first-child, th:first-child {{ text-align:left; }}
 .cap {{ font-weight:600; margin: 12px 0; }}
</style>

<h2>Top {topk} ΔBLEU (instruct − base)</h2>
<table>
<tr><th>id</th><th>BLEU(base)</th><th>BLEU(instr)</th><th>ΔBLEU</th><th>chrF(base)</th><th>chrF(instr)</th><th>ΔchrF</th><th>ROUGE(base)</th><th>ROUGE(instr)</th><th>ΔROUGE</th></tr>
{''.join(row_html(x) for x in up)}
</table>

<h2>Bottom {topk} ΔBLEU</h2>
<table>
<tr><th>id</th><th>BLEU(base)</th><th>BLEU(instr)</th><th>ΔBLEU</th><th>chrF(base)</th><th>chrF(instr)</th><th>ΔchrF</th><th>ROUGE(base)</th><th>ROUGE(instr)</th><th>ΔROUGE</th></tr>
{''.join(row_html(x) for x in down)}
</table>
<p class="cap">Note: per-id sentence-level scores (sacrebleu/rouge-score). Δ = instr − base.</p>
"""

    os.makedirs(FDIR, exist_ok=True)
    with open(os.path.join(FDIR, "error_board.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] wrote figs/error_board.html")

if __name__ == "__main__":
    ensure_dirs()
    gen_tables()
    gen_error_board()