# Release Notes — v0.3-baseline-lite

- Generated: 2025-08-24 07:19:34
- Commit: `45d8abbb`
- Raw dir (final): `C:/Project/LLM/results/raw_patched`

## Latency Summary

| mode | count | mean(ms) | p50 | p95 | min | max |
|---|---:|---:|---:|---:|---:|---:|
| general | 60 | 9899.783333333333 | 9959.0 | 18911.95 | 3294.0 | 19706.0 |
| instructed | 60 | 7765.766666666666 | 6723.0 | 12888.849999999995 | 3044.0 | 15056.0 |

## Metrics Snapshot

# Metrics Snapshot

- source: `C:/Project/LLM/results/quantitative/stats_summary.csv`

| metric | ci_low | ci_high |
|---|---|---|
| bleu | 0.23837522096126434 | 1.9334287568965325 |
| chrf | -0.2642577718005459 | 3.3057833703624824 |
| rougeL | -1.0732323232323233 | 1.5814393939393938 |

## Compliance Snapshot

# Compliance Snapshot

- source: `C:/Project/LLM/results/quantitative/compliance_summary.csv`

| metric | general | instructed |
|---|---:|---:|
| format_json | 1.000 | 1.000 |
| limit_chars | 1.000 | 1.000 |
| bullets_min_n | 1.000 | 1.000 |
| limit_items_json | 1.000 | 1.000 |
| forbid_terms | 1.000 | 1.000 |

## Environment Snapshot

환경표 (env_table) — Baseline Freeze

- 생성시각: 2025-08-24T03:41:15+09:00
- 담당: 유다영
- 목적: v0.3-baseline 재현을 위한 환경/설정/입출력 고정 기록

A. System
| 항목 | 값 |
|---|---|
| OS | Windows-10-10.0.26100-SP0 |
| 호스트 모델 | ASUS ROG Strix G531GU (ASUSTeK) |
| CPU | Intel(R) Core(TM) i7-9750H @ 2.60 GHz (MaxClock 2592 MHz) |
| RAM | 15.9 GB (TotalPhysicalMemory 17,022,259,200 bytes) |
| GPU | NVIDIA GeForce GTX 1660 Ti, 6 GB (6144 MiB) |
| Driver / CUDA | Driver 555.97, CUDA 12.5 |
| Disk | C: 전체 476.03 GB (사용 309.16 / 여유 166.87) · D: 전체 1,862.95 GB (사용 15.59 / 여유 1,847.36) |

> 원자료: `nvidia-smi` / PowerShell 디스크 출력 / WMI CPU·메모리 정보

B. Python & Tooling (프로젝트 venv 기준)
| 항목 | 값 |
|---|---|
| Python | 3.12 (venv) |
| venv 경로 | `C:\Project\LLM\.venv` |
| Pip | 25.2 |
| Git | 2.46.1.windows.1 |
| Ollama | 0.5.3 |

 `pip freeze` 스냅샷은 파일로 보관:  
  `python -m pip freeze > docs\pip_freeze.txt`

C. Key Packages (고정 버전)
| 패키지 | 버전 |
|---|---|
| langchain | 0.3.27 |
| langchain-core | 0.3.74 |
| langchain-community | 0.3.27 |
| langchain-openai | 0.3.29 |
| langchain-ollama | 0.3.6 |
| sacrebleu | 2.5.1 |
| rouge-score | 0.1.2 |
| pandas | 2.3.1 |
| scipy | 1.16.1 |
| matplotlib | 3.10.5 |
| jsonschema | 4.25.0 |

D. Models & Serving
| 항목 | 값 |
|---|---|
| Provider | Ollama |
| General | `gemma:7b` (digest/sha: ef311de6af9db043d51ca4b1e766c28e0a1ac41d60420fed5e001dc470c64b77) |
| Instruct | `gemma:7b-instruct` (digest/sha: ef311de6af9db043d51ca4b1e766c28e0a1ac41d60420fed5e001dc470c64b77) |

> 확인 명령: `ollama show <model> --modelfile` 의 `FROM ...\sha256-...`

E. Dataset / Prompts Integrity
| 파일 | 경로 | SHA-256 해시 |
|---|---|---|
| prompts | `prompts\prompts.csv` | B20B9715B265B21BC0DC28DC8836DEFFD592B07EC606DB7857EB64A67AF1B6B7 |
| reference | `reference\reference_corpus.jsonl` | 2FAA26852992A37A41126D7703C91058792073D02665F2EEB221049E3F1B1458 |

F. Baseline Decoding (고정)
| 파라미터 | 값 |
|---|---|
| seed | 42 |
| temperature | 0.0 |
| top_p | 1.0 |
| max_tokens | 512 |
| stop | (없음) |

G. Git Snapshot
| 항목 | 값 |
|---|---|
| Branch | `main` |
| Commit | 066e19ea |
| Tag | `v0.3-baseline` |
| Remote | origin (GitHub) |

H. 재현 절차(요약)
1. venv 활성화 → 의존성 설치 (`pip freeze`를 `docs\pip_freeze.txt`로 저장)  
2. `configs/baseline.yaml`로 파라미터 고정  
3. `scripts\baseline_run.bat` 실행 → `logs\baseline_YYYYMMDD.out` 생성  
4. 결과 폴더/지표 값이 이전 baseline과 완전 일치 확인(정렬·평가·통계까지)
