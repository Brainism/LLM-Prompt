# LLM-Prompt Main Dataset (v1)
- Generated: 2025-08-19T17:55:00.151425+00:00
- Purpose: Main experimental set for prompt evaluation (summarization, QA, information extraction).
- License: CC BY 4.0 (synthetic, human-curated references). Cite this card when reusing.

## Composition
- Total items: 120 (SUM=40, QA=40, IE=40)
- Languages: ko (~60%), en (~40%)
- Length bins: short ≤120w, medium 121–360w, long ≥361w (approx. by whitespace tokens)
- Difficulty bins: easy/normal/hard (heuristic)
- cluster_id: unique per item (no paraphrase clusters in main set; use robustness set separately)

## Files
- data/raw/prompts/prompts.jsonl
- data/raw/references/references.jsonl
- data/raw/metadata/meta.jsonl
- data/manifest/split_manifest_main.json
- rules/json_schema_main.json

## Notes
- References are concise gold summaries/answers structured for evaluation.
- Information extraction references are JSON strings validated by `rules/json_schema_main.json`.
- No PII included; synthetic content mimics realistic topics (tech, policy, health, environment, science).
