## Domains & Tasks
- Domains: {일반질문, 정직업무, 규칙지키기(금칙어/JSON/길이), 코딩요약 등}
- Languages: ko/en (균형)
- Length bins: short / medium / long (문자 수 기준, schema 참조)
- Difficulty bins: easy / medium / hard

## Sampling
- n (pair): ≥ 60 (현재), 향후 확장 목표: 1500 (ko/en 균형, 길이/난이도 균형)
- Source mix: 공개참조 60%, 과제/인검 20%, 규칙태스크 20%
- Duplicates: 유사도 ≥0.9 자동 중복 제거 (클러스터 기준)

## Exclusion
- PII/금칙: PII/욕설/BNF 규칙 위반 자동 필터
- 포맷: JSON 스키마 불일치, 길이 초과, 금칙어 위반 시 제외(혹은 Fail 기록)

## DoD (Scope)
- 도메인×언어×길이×난이도 분포표 존재
- data/manifest/split_manifest_main.json 스키마 검증 통과 로그 첨부
- dataset_card.md / data_report.pdf 링크