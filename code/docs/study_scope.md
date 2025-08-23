Study Scope — LLM-Prompt (v0.3-baseline-lite 후속)

1. 목적
Gemma 7B(general) vs Gemma 7B-instruct의 한국어 중심 성능·준수율·효율 비교.

2. 데이터 범위
샘플 수: 60 (prompts/prompts.csv 기준, id=1..60 가정)
언어: 한국어(입력), 출력 한국어 우선
주제 도메인: 일반지식/요약/지시이행 혼합(메타데이터 없을 시 `domain="general"`로 표기)
길이: 입력 글자수/토큰 분포 보고(데이터 리포트에서 요약)

3. 모델·설정(고정)
Provider: Ollama
Models: gemma:7b, gemma:7b-instruct (sha256 동일)
Decoding: seed=42, temperature=0.0, top_p=1.0, max_tokens=512  (스모크 시 256 일시 허용)
Context: num_ctx=2048 (VRAM 제약 시 1024 허용, 보고서에 명시)

4. 산출물
정량: BLEU, ROUGE-L, chrF (추후 BERTScore F1 추가 예정)
준수율: format-json / forbid-terms / bullets / limit-*(chars/items) 규칙 준수율
효율: latency_ms(p50/p95), cost_usd(있을 시)

5. 제외/탈락 기준
출력 비어있음/형식 실패/치명 오류: 해당 샘플을 비교 집계에서 제외, 사유 기록
프롬프트-레퍼런스 정렬 실패: `aligned_texts.py` 재시도 후 지속 실패 시 제외

6. 재현성
`docs/env_table.md` + `docs/pip_freeze.txt` + 태그 `v0.3-baseline-lite`
실행 로그: `logs/` 폴더 내 배치 로그 보관
