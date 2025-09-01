from datetime import datetime
from pathlib import Path
from textwrap import dedent

DOCS = Path("docs")
DOCS.mkdir(parents=True, exist_ok=True)

study_scope = dedent(f"""\
# Study Scope (v1)
- Generated at: {datetime.utcnow().isoformat()}Z

## 1. Domains (select 1-2 for 理쒖냼 ?뚮옖)
- [x] Summarization (news/abstract)
- [x] QA (short-form factual)
- [ ] Translation
- [ ] Information Extraction (JSON)

## 2. Languages
- [x] Korean (primary, 60%)
- [x] English (secondary, 40%)

## 3. Length bins (by input tokens)
- [x] Short (??120)
- [x] Medium (121-360)
- [x] Long (??361)

## 4. Difficulty bins
- [x] Easy
- [x] Normal
- [x] Hard

## 5. Target sample size (理쒖냼 ?뚮옖)
- [x] Total n ??50
- [x] Per-bin minimum share ??15% (length & difficulty)
- [x] Robustness set: paraphrases 10-15% with cluster_id

## 6. Sources & License (fill)
- Public benchmarks (60%): <list with license>
- Teacher?묱uman (20%): <who/criteria>
- Rule-based tasks (20%): <schema path>
""")

analysis_plan = dedent(f"""\
# Analysis Plan (Preregistered) ??v1
- Generated at: {datetime.utcnow().isoformat()}Z
- Principle: **媛??以묒떖 / 蹂寃?湲덉?(蹂寃????ъ쑀 湲곕줉)**

## A. Hypotheses (3-5 core)
- **H1 (Similarity):** Prompt A has higher **ROUGE-L (median)** than B by **??+1.0pt** on Summarization.
- **H2 (Interaction):** The **BERTScore F1** gain of A over B is larger on **Long** inputs vs **Short**.
- **H3 (Compliance):** **JSON validity & required-key rate** is higher for A than B on QA/IE-style outputs.

## B. Primary / Secondary metrics
- **Primary:** ROUGE-1/2/L, **BERTScore F1**
- **Compliance:** JSON schema validity, required-key inclusion, forbidden-terms violation rate
- **Efficiency:** Token cost, latency p50/p95
- **Robustness:** Paraphrase / word-order perturbation retention rate

## C. Data & Splits (link to manifest)
- Target n ??50, stratified by domain, length, difficulty, language
- Robustness clusters with `cluster_id`; **cluster-aware resampling** in stats
- Exclusion rules: empty output, truncation/token overflow, corrupted reference

## D. Statistical plan
- **Paired bootstrap** (iterations: 10000, CI: 95%)
- **Wilcoxon signed-rank** (two-sided) on per-item deltas
- Report **effect size (dz)**; **BH-FDR** for multiple comparisons
- For robustness: resample **by cluster** (not item) to avoid N inflation

## E. Logging schema (must exist in result logs)
- item_id, domain, lang, len_bin, diff_bin, cluster_id
- prompt_id, model_id, seed, temperature, top_p, max_tokens
- metrics: rouge1/2/L, bertscore_f1, json_valid, req_keys_rate, forbid_viol, tok_cost, lat_p50, lat_p95

## F. Stopping / Gate
- Proceed to writing if ??/3 core H pass with q<0.05 or dz??.3 and CI excludes 0
- Otherwise expand n (toward 80-120) or strengthen ablation

## G. Deviations
- Any change to H1-H3 or o/iter must be recorded here with timestamp & rationale
""")

(DOCS / "study_scope.md").write_text(study_scope, encoding="utf-8")
(DOCS / "analysis_plan.md").write_text(analysis_plan, encoding="utf-8")
print("[init_m1] wrote docs/study_scope.md and docs/analysis_plan.md")
