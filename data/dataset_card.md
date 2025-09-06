## Overview
- Size: n=60 pairs (ko/en 균형), 길이/난이도 bin 포함
- Tasks: 규칙 따르기(JSON/길이/금칙), 일반 QA, 요약/변환 등
- Structure: id, input, reference, domain, lang, len_bin, diff_bin, cluster_id, license, n_chars …

## Provenance & License
- Sources: 공개참조 60%, 과제/인검 20%, 규칙태스크 20%
- License: {명시}, 3rd-party text는 원 출처 링크
- PII: 자동 필터

## Preprocessing
- Canonize → prompts/main.csv
- Manifest schema validate (scripts/validate_manifest.py)
- Dedup by cluster_id + similarity ≥0.9

## Known Limitations
- 특정 도메인 과대표집 가능성
- 번역체 문장 혼입 가능성

## Usage & Split
- Single split for now (n=60 pairs)
- Future: train/dev/test 혹은 k-fold
