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
    except:
        return na


def main(stats, summary, figdir, out):
    stats_rows = read_stats(stats) if stats and Path(stats).exists() else []
    figdir = Path(figdir) if figdir else Path("results/figures")

    md = []
    md.append("# 📊 LLM Prompt v0.4 결과 요약")
    md.append("")
    md.append("## 1) 통계 요약")
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
        md.append("- (통계 파일 없음)")

    md.append("")
    md.append("## 2) 컴플라이언스 시각화")
    p1 = figdir / "compliance_passrate_by_model_mode.png"
    p2 = figdir / "compliance_top_fail_rules.png"
    if p1.exists():
        md.append(f"![passrate_by_model_mode]({p1.as_posix()})")
    else:
        md.append("- pass rate 그래프 없음")
    if p2.exists():
        md.append(f"![top_fail_rules]({p2.as_posix()})")
    else:
        md.append("- top failing rules 그래프 없음")

    md.append("")
    md.append("## 3) 액션 아이템(제안)")
    md.append("1. 상위 실패 규칙 대상 가드레일/프롬프트 가이드 강화")
    md.append("2. 데이터 증강(실패 규칙 유사 샘플 추가) 및 재평가")
    md.append("3. 모델/모드 조합 중 pass rate 상위 설정을 기본값으로 채택")
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
