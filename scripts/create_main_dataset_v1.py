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
        "湲곗닠",
        "援?궡 ???ㅽ??몄뾽????꾨젰 LLM 媛??蹂대뱶瑜?怨듦컻?덈떎. 蹂대뱶???ｌ? ?μ튂?먯꽌 ?⑤뵒諛붿씠??異붾줎??紐⑺몴濡??섎ŉ, ?묒옄?붿? 罹먯떛 理쒖쟻?붾? ?댁옣?덈떎. 異쒖떆 珥덇린?먮뒗 媛쒕컻 ?ㅽ듃 ?뺥깭濡?諛고룷?섎ŉ, ?대뀈 1遺꾧린遺???곗뾽??紐⑤뱢??怨듦툒???덉젙?대떎.",
    ),
    (
        "ko",
        "蹂닿굔",
        "?ы빐 ?낃컧 ?좏뻾 ?쒓린媛 ?덈뀈蹂대떎 ?욌떦寃⑥죱?? 諛⑹뿭?밴뎅? 怨좎쐞?섍뎔?먭쾶 ?덈갑?묒쥌??沅뚭퀬?섍퀬, ?숆탳? ?붿뼇?쒖꽕?????꾩깮怨??섍린 吏移⑥쓣 ?ш컯議고뻽?? ?꾨Ц媛?ㅼ? 留덉뒪??李⑹슜???ㅻ궡 諛吏??섍꼍?먯꽌 ?ъ쟾???좏슚???덈갑 ?섎떒?대씪怨?留먰뻽??",
    ),
    (
        "ko",
        "?뺤콉",
        "?덈줈???곗씠??蹂댄샇 吏移⑥씠 ?뺤젙?섏뼱 怨듦났湲곌???誘쇨컧?뺣낫 痍④툒 湲곗???媛뺥솕?먮떎. 遺꾩궛 蹂닿?怨??묎렐 ?듭젣 濡쒓렇 ?섎Т?붽? ?듭떖?대ŉ, ?꾨컲 ??怨쇱쭠湲??곹븳???곹뼢?먮떎.",
    ),
    (
        "ko",
        "?섍꼍",
        "?⑦빐???곸“ 寃쎈낫媛 諛쒕졊?섏뿀?? ?섏삩 ?곸듅怨?媛뺥븳 ?쇱궗?됱씠 蹂듯빀?곸쑝濡??묒슜?덈떎??遺꾩꽍???섏솕?? ?묒떇???쇳빐瑜?以꾩씠湲??꾪빐 ?곗냼 怨듦툒怨?癒뱀씠??議곗젅??沅뚭퀬?쒕떎.",
    ),
    (
        "ko",
        "怨쇳븰",
        "援?궡 ?곌뎄吏꾩씠 2李⑥썝 諛섎룄泥??뚯옱??寃고븿 ?쒖뼱 湲곗닠??諛쒗몴?덈떎. 寃고븿 諛?꾨? 湲곗〈 ?鍮?40% ??텛???꾩옄 ?대룞?꾧? ?μ긽?섏뿀??",
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
    ("ko", "??쒕?援?쓽 ?섎룄??臾댁뾿?멸??", "?쒖슱", "easy"),
    ("ko", "鍮쏆쓽 ?띾룄??吏꾧났?먯꽌 珥덈떦 ??紐?km?멸??", "??300,000 km", "normal"),
    ("ko", "?뚯씠?ъ뿉??由ъ뒪?몄쓽 湲몄씠瑜?諛섑솚?섎뒗 ?댁옣 ?⑥닔??", "len", "easy"),
    ("ko", "?쒕컲?꾩뿉??媛???믪? ?곗??", "諛깅몢??, "normal"),
    ("ko", "愿묓빀?깆쓽 二쇱슂 ?곕Ъ? 臾댁뾿?멸??", "?щ룄?밴낵 ?곗냼", "easy"),
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
        '?ㅼ쓬 ?댁뒪?먯꽌 ?ш굔 ?뺣낫瑜?JSON?쇰줈 異붿텧?섎씪. ?꾨뱶: title, date(YYYY-MM-DD), location, involved, summary. 蹂몃Ц: "{text}"',
    ),
    (
        "en",
        'From the following report, extract JSON with fields: title, date(YYYY-MM-DD), location, involved, summary. Text: "{text}"',
    ),
]
IE_SOURCES = [
    (
        "ko",
        "?쒖슱 吏?섏쿋 2?몄꽑 ?쇰? 援ш컙?먯꽌 ?좏샇 ?μ븷媛 諛쒖깮??異쒓렐湲?吏?곗씠 鍮싳뼱議뚮떎. 肄붾젅?쇱? ?꾩떆 議곗튂瑜??듯빐 諛곗감 媛꾧꺽??議곗젙?섍퀬, ?먯씤 遺꾩꽍??吏꾪뻾 以묒씠?쇨퀬 諛앺삍??",
        {
            "title": "吏?섏쿋 2?몄꽑 ?좏샇 ?μ븷",
            "date": "2025-08-18",
            "location": "?쒖슱",
            "involved": "肄붾젅??,
            "summary": "?좏샇 ?μ븷濡?吏??諛쒖깮, ?꾩떆 議곗튂? ?먯씤 遺꾩꽍 吏꾪뻾",
        },
    ),
    (
        "ko",
        "?⑤? 吏??뿉 ?쒓컙??50mm??媛뺥븳 鍮꾧? ?잛븘???꾨줈 移⑥닔媛 蹂닿퀬?섏뿀?? 吏諛⑹옄移섎떒泥대뒗 ?섏쿇 二쇰? ?묎렐???먯젣?섎씪怨??밸??덈떎.",
        {
            "title": "?⑤? 吏??吏묒쨷?몄슦",
            "date": "2025-08-15",
            "location": "?⑤? 吏??,
            "involved": "吏?먯껜",
            "summary": "吏묒쨷?몄슦濡??꾨줈 移⑥닔, ?섏쿇 ?묎렐 ?먯젣 ?밸?",
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
                f"?ㅼ쓬 湲곗궗瑜?2~3臾몄옣?쇰줈 ?붿빟?섎씪:\n{text}"
                if lang == "ko"
                else f"Summarize the following article in 2?? sentences:\n{text}"
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
- Length bins: short ??20w, medium 121??60w, long ??61w (approx. by whitespace tokens)
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
