from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".").resolve()
RAW_PROMPTS = ROOT / "data" / "raw" / "prompts"
RAW_REFS = ROOT / "data" / "raw" / "references"
RAW_META = ROOT / "data" / "raw" / "metadata"
MANIFEST = ROOT / "data" / "manifest"
RULES = ROOT / "rules"
DOCS = ROOT / "docs"

for p in [RAW_PROMPTS, RAW_REFS, RAW_META, MANIFEST, RULES, DOCS]:
    p.mkdir(parents=True, exist_ok=True)


def length_bin(text: str) -> str:
    n = len(text.split())
    if n <= 120:
        return "short"
    if n <= 360:
        return "medium"
    return "long"


def make_id(prefix: str, i: int) -> str:
    return f"{prefix}_{i:04d}"


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


random.seed(7)

SUMM_THEMES = [
    (
        "ko",
        "기술",
        "국내 한 스타트업이 저전력 LLM 가속 보드를 공개했다. 보드는 엣지 장치에서 온디바이스 추론을 목표로 하며, 양자화와 캐싱 최적화를 내장했다. 출시 초기에는 개발 키트 형태로 배포되며, 내년 1분기부터 산업용 모듈이 공급될 예정이다.",
    ),
    (
        "ko",
        "보건",
        "올해 독감 유행 시기가 예년보다 앞당겨졌다. 방역당국은 고위험군에게 예방접종을 권고하고, 학교와 요양시설에 손 위생과 환기 지침을 재강조했다. 전문가들은 마스크 착용이 실내 밀집 환경에서 여전히 유효한 예방 수단이라고 말했다.",
    ),
    (
        "ko",
        "정책",
        "새로운 데이터 보호 지침이 확정되어 공공기관의 민감정보 취급 기준이 강화됐다. 분산 보관과 접근 통제 로그 의무화가 핵심이며, 위반 시 과징금 상한도 상향됐다.",
    ),
    (
        "ko",
        "환경",
        "남해안 적조 경보가 발령되었다. 수온 상승과 강한 일사량이 복합적으로 작용했다는 분석이 나왔다. 양식장 피해를 줄이기 위해 산소 공급과 먹이량 조절이 권고된다.",
    ),
    (
        "ko",
        "과학",
        "국내 연구진이 2차원 반도체 소재의 결함 제어 기술을 발표했다. 결함 밀도를 기존 대비 40% 낮추어 전자 이동도가 향상되었다.",
    ),
    (
        "en",
        "technology",
        "A local startup unveiled a low-power LLM accelerator board designed for on-device inference at the edge. It integrates quantization and KV-cache optimizations and will ship as a dev kit before moving to industrial modules next quarter.",
    ),
    (
        "en",
        "health",
        "Seasonal influenza is arriving earlier than usual. Authorities recommend vaccination for high-risk groups and reiterate hand hygiene and ventilation guidance for schools and nursing homes.",
    ),
    (
        "en",
        "policy",
        "A revised data-protection directive tightens standards for handling sensitive information in public institutions, mandating access-log auditing and distributed storage.",
    ),
    (
        "en",
        "science",
        "Researchers reported a method to reduce defect density in 2D semiconductors by 40%, boosting carrier mobility and stability under heat stress.",
    ),
    (
        "en",
        "environment",
        "Red tide warnings were issued along the southern coast. Warm water and intense sunlight are believed to be the main drivers; fish farms are advised to increase aeration and adjust feeding.",
    ),
]

QA_ITEMS = [
    ("ko", "대한민국의 수도는 무엇인가?", "서울", "easy"),
    ("ko", "빛의 속도는 진공에서 초당 약 몇 km인가?", "약 300,000 km", "normal"),
    ("ko", "파이썬에서 리스트의 길이를 반환하는 내장 함수는?", "len", "easy"),
    ("ko", "한반도에서 가장 높은 산은?", "백두산", "normal"),
    ("ko", "광합성의 주요 산물은 무엇인가?", "포도당과 산소", "easy"),
    ("en", "What is the capital of South Korea?", "Seoul", "easy"),
    (
        "en",
        "Which algorithm has time complexity O(n log n) for average sorting?",
        "Merge sort (also quicksort average)",
        "normal",
    ),
    ("en", "Who proposed the theory of general relativity?", "Albert Einstein", "easy"),
    (
        "en",
        "Which organ primarily regulates blood glucose via insulin?",
        "Pancreas",
        "normal",
    ),
    ("en", "What is the chemical symbol for sodium?", "Na", "easy"),
]

IE_TEMPLATES = [
    (
        "ko",
        '다음 뉴스에서 사건 정보를 JSON으로 추출하라. 필드: title, date(YYYY-MM-DD), location, involved, summary. 본문: "{text}"',
    ),
    (
        "en",
        'From the following report, extract JSON with fields: title, date(YYYY-MM-DD), location, involved, summary. Text: "{text}"',
    ),
]
IE_SOURCES = [
    (
        "ko",
        "서울 지하철 2호선 일부 구간에서 신호 장애가 발생해 출근길 지연이 빚어졌다. 코레일은 임시 조치를 통해 배차 간격을 조정하고, 원인 분석을 진행 중이라고 밝혔다.",
        {
            "title": "지하철 2호선 신호 장애",
            "date": "2025-08-18",
            "location": "서울",
            "involved": "코레일",
            "summary": "신호 장애로 지연 발생, 임시 조치와 원인 분석 진행",
        },
    ),
    (
        "ko",
        "남부 지역에 시간당 50mm의 강한 비가 쏟아져 도로 침수가 보고되었다. 지방자치단체는 하천 주변 접근을 자제하라고 당부했다.",
        {
            "title": "남부 지역 집중호우",
            "date": "2025-08-15",
            "location": "남부 지역",
            "involved": "지자체",
            "summary": "집중호우로 도로 침수, 하천 접근 자제 당부",
        },
    ),
    (
        "en",
        "A data breach at a municipal office exposed resident records. The authority launched an investigation and mandated password resets.",
        {
            "title": "Municipal data breach",
            "date": "2025-08-10",
            "location": "Municipal office",
            "involved": "Local authority",
            "summary": "Records exposed; investigation and password resets underway",
        },
    ),
    (
        "en",
        "A magnitude-5.2 earthquake was recorded offshore, with minor damages reported in nearby towns.",
        {
            "title": "Offshore earthquake 5.2",
            "date": "2025-08-01",
            "location": "Offshore",
            "involved": "Regional agency",
            "summary": "Minor damages reported in nearby towns after quake",
        },
    ),
]

N_SUM, N_QA, N_IE = 40, 40, 40

prompts, refs, meta = [], [], []

for i in range(N_SUM):
    lang, theme, base = random.choice(SUMM_THEMES)
    rep = random.choice([1, 2, 3])
    text = " ".join([base] * rep)
    sents = [s.strip() for s in text.replace("?", ".").split(".") if s.strip()]
    refsum = ". ".join(sents[:2]) + "." if sents else text
    item_id = make_id("SUM", i)
    diff = random.choice(["easy", "normal", "hard"])
    prompts.append(
        {
            "id": item_id,
            "input": (
                f"다음 기사를 2~3문장으로 요약하라:\n{text}"
                if lang == "ko"
                else f"Summarize the following article in 2–3 sentences:\n{text}"
            ),
            "domain": "summarization",
            "lang": lang,
            "diff_bin": diff,
            "cluster_id": item_id,
        }
    )
    refs.append({"id": item_id, "reference": refsum})
    meta.append(
        {
            "id": item_id,
            "domain": "summarization",
            "lang": lang,
            "diff_bin": diff,
            "cluster_id": item_id,
            "len_bin": length_bin(text),
        }
    )

for i in range(N_QA):
    lang, q, a, diff = random.choice(QA_ITEMS)
    item_id = make_id("QA", i)
    prompts.append(
        {
            "id": item_id,
            "input": q,
            "domain": "qa",
            "lang": lang,
            "diff_bin": diff,
            "cluster_id": item_id,
        }
    )
    refs.append({"id": item_id, "reference": a})
    meta.append(
        {
            "id": item_id,
            "domain": "qa",
            "lang": lang,
            "diff_bin": diff,
            "cluster_id": item_id,
            "len_bin": length_bin(q),
        }
    )

for i in range(N_IE):
    lang, template = random.choice([t for t in IE_TEMPLATES if t[0] in ("ko", "en")])
    src_candidates = [s for s in IE_SOURCES if s[0] == lang] or IE_SOURCES
    s_lang, text, gold = random.choice(src_candidates)
    prompt_text = template.format(text=text)
    item_id = make_id("IE", i)
    diff = random.choice(["normal", "hard"])
    prompts.append(
        {
            "id": item_id,
            "input": prompt_text,
            "domain": "information_extraction",
            "lang": lang,
            "diff_bin": diff,
            "cluster_id": item_id,
        }
    )
    refs.append({"id": item_id, "reference": json.dumps(gold, ensure_ascii=False)})
    meta.append(
        {
            "id": item_id,
            "domain": "information_extraction",
            "lang": lang,
            "diff_bin": "normal",
            "cluster_id": item_id,
            "len_bin": length_bin(text),
        }
    )

write_jsonl(RAW_PROMPTS / "prompts.jsonl", prompts)
write_jsonl(RAW_REFS / "references.jsonl", refs)
write_jsonl(RAW_META / "meta.jsonl", meta)

manifest = [
    {k: m[k] for k in ["id", "domain", "lang", "len_bin", "diff_bin", "cluster_id"]}
    for m in meta
]
(MANIFEST / "split_manifest_main.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)

schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Event Extraction",
    "type": "object",
    "required": ["title", "date", "location", "involved", "summary"],
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
        "location": {"type": "string", "minLength": 1},
        "involved": {"type": "string", "minLength": 1},
        "summary": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
}
(RULES / "json_schema_main.json").write_text(
    json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
)

dataset_card = f"""# LLM-Prompt Main Dataset (v1)
- Generated: {datetime.now(timezone.utc).isoformat()}
- Purpose: Main experimental set for prompt evaluation (summarization, QA, information extraction).
- License: CC BY 4.0 (synthetic, human-curated references). Cite this card when reusing.

## Composition
- Total items: {len(manifest)} (SUM={N_SUM}, QA={N_QA}, IE={N_IE})
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
"""
(DOCS / "dataset_card.md").write_text(dataset_card, encoding="utf-8")

print("[main-dataset] done.")
print("  - data/raw/prompts/prompts.jsonl")
print("  - data/raw/references/references.jsonl")
print("  - data/raw/metadata/meta.jsonl")
print("  - data/manifest/split_manifest_main.json")
print("  - rules/json_schema_main.json")
print("  - docs/dataset_card.md")
