Analysis Plan — LLM-Prompt

1. 가설(H)
H1(품질): instructed가 general보다 BLEU 평균이 높다.
H2(일관): instructed와 general의 ROUGE-L, chrF 차이는 0이 아니다(양·음 미지정).
H3(준수): instructed가 규칙 준수율(형식/금칙어/불릿/길이)에서 더 높다.

2. 1·2차 지표
1차: BLEU
2차: ROUGE-L, chrF, (추가) BERTScore F1 보조: 규칙준수율(%), latency_ms p50/p95, cost_usd(선택)

3. 통계 기법(사전 등록)
부트스트랩(표본=10,000, seed=42), 95% CI
Wilcoxon signed-rank (쌍대 비교), α=0.05
다중비교 보정: Benjamini–Hochberg FDR (q값 보고)
효과크기: Cohen’s d (또는 dz)

4. 절차
prompts ↔ raw 1:1 정합 확인(60/60)  
BLEU/ROUGE/chrF 계산 → `results/quantitative/*.json`  
`stats_tests_plus.py`로 평균/Δ/CI/p/q/d 산출 → `stats_summary.csv`  
준수율·효율 로그 결합(추가) → 테이블/그림 작성

5. 보고
표: 평균±CI, Δ(절대·%), p, q, d
그림: per-item waterfall, 분포, 오류보드(위반 Top 사례)
제한점: 한국어 `limit-words` 불안정 → `limit-chars/items` 대체 사용