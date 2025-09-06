## Hypotheses
- H1 (품질): instructed − general 의 BLEU ⟫ 0
- H2 (구조): instructed − general 의 ROUGE-L ≈ 0 (불확실)
- H3 (문자기반): instructed − general 의 chrF ≈ 0 (불확실)
- Compliance Δ: 0 (동수) 가정

## Metrics
- 1차: BLEU (sacreBLEU sentence), ROUGE-L (F1), chrF
- 2차(선택): BERTScore F1
- Efficiency: latency (p50/p95)

## Statistics
- Paired Bootstrap (≥10k) for Δ mean 95% CI
- Wilcoxon signed-rank test (two-sided)
- Effect size: Cohen’s d_z (paired)
- Multiple tests: Benjamini–Hochberg FDR (q=0.05)
- Unit: per-id pair (n=items)

## Decision
- 유의: CI가 0 미포함 & q<0.05
- Report: Δ, Δ%, d, CI, p, q 전부 표기

## DoD (Analysis)
- tables/stats.csv (BLEU/ROUGE-L/chrF/[BERTScore])
- tables/metrics.csv (집계), tables/latency.csv (p50/p95)
- figs/error_board.html (상/하위 Δ 사례 스니펫)