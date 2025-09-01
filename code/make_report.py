import argparse
import csv
from pathlib import Path


def read_stats(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def fmt(x, nd=2, na=""):
    try:
        v = float(x)
        if v != v:
            return na
        return f"{v:.{nd}f}"
    except Exception:return na


def main(stats, summary, figdir, out):
    stats_rows = read_stats(stats) if stats and Path(stats).exists() else []
    figdir = Path(figdir) if figdir else Path("results/figures")

    md = []
    md.append("# ?뱤 LLM Prompt v0.4 寃곌낵 ?붿빟")
    md.append("")
    md.append("## 1) ?듦퀎 ?붿빟")
    if stats_rows:
        md.append("")
        md.append("| metric | n | mean_diff | 95% CI | p | q_fdr | Cohen's d |")
        md.append("|---|---:|---:|---:|---:|---:|---:|")
        for r in stats_rows:
            ci = f"[{fmt(r.get('ci_lo'))}, {fmt(r.get('ci_hi'))}]"
            md.append(
                f"| {r.get('metric','')} | {r.get('n','')} | {fmt(r.get('mean_diff'))} | {ci} | {fmt(r.get('p'))} | {fmt(r.get('q_fdr'))} | {fmt(r.get('cohens_d'))} |"
            )
    else:
        md.append("- (?듦퀎 ?뚯씪 ?놁쓬)")

    md.append("")
    md.append("## 2) 而댄뵆?쇱씠?몄뒪 ?쒓컖??)
    p1 = figdir / "compliance_passrate_by_model_mode.png"
    p2 = figdir / "compliance_top_fail_rules.png"
    if p1.exists():
        md.append(f"![passrate_by_model_mode]({p1.as_posix()})")
    else:
        md.append("- pass rate 洹몃옒???놁쓬")
    if p2.exists():
        md.append(f"![top_fail_rules]({p2.as_posix()})")
    else:
        md.append("- top failing rules 洹몃옒???놁쓬")

    md.append("")
    md.append("## 3) ?≪뀡 ?꾩씠???쒖븞)")
    md.append("1. ?곸쐞 ?ㅽ뙣 洹쒖튃 ???媛?쒕젅???꾨＼?꾪듃 媛?대뱶 媛뺥솕")
    md.append("2. ?곗씠??利앷컯(?ㅽ뙣 洹쒖튃 ?좎궗 ?섑뵆 異붽?) 諛??ы룊媛")
    md.append("3. 紐⑤뜽/紐⑤뱶 議고빀 以?pass rate ?곸쐞 ?ㅼ젙??湲곕낯媛믪쑝濡?梨꾪깮")
    md.append("")

    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(md), encoding="utf-8")
    print(f"[OK] wrote report: {outp}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default=r"results\quantitative\stats_summary.csv")
    ap.add_argument("--summary", default=r"results\quantitative\compliance_summary.csv")
    ap.add_argument("--figdir", default=r"results\figures")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main(a.stats, a.summary, a.figdir, a.out)
