from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import json, random, argparse

@dataclass
class Item:
    id: str
    input: str
    reference: str
    domain: str
    lang: str
    diff_bin: str
    cluster_id: str

KO_SOURCES = [
    ("요약", "인공지능 모델은 다양한 도메인에서 활용되고 있다. 최근에는 프롬프트 엔지니어링이 성능에 매우 큰 영향을 미친다는 점이 밝혀졌다. 본 문서는 프롬프트 설계 원칙과 평가 방법을 간단히 정리한다. 또한 재현성과 통계 검정의 중요성을 강조한다."),
    ("요약", "데이터 전처리는 모델 성능의 기반이다. 텍스트 정규화, 토큰화 규칙, 금칙어, JSON 스키마 준수 등은 일관적으로 관리되어야 한다. 이 가이드는 실무 환경에서 흔히 발생하는 오류를 줄이기 위한 체크리스트를 제공한다."),
    ("QA",  "대한민국의 수도는 어디인가? 배경지식에 따르면 서울특별시가 행정수도 역할을 수행하고 있다."),
]
EN_SOURCES = [
    ("summarization", "Large language models are increasingly used across domains. Prompt design substantially influences outcomes. This note outlines prompt principles, evaluation metrics, reproducibility, and statistical testing."),
    ("summarization", "Data preprocessing underpins model performance. Normalization, tokenization, forbidden terms, and JSON schema compliance should be enforced consistently to reduce common production errors."),
    ("qa", "What is the capital of South Korea? Based on background knowledge, Seoul is the administrative capital."),
]

def shortify(txt: str, n_sent: int = 2) -> str:
    # 매우 단순한 '레퍼런스 요약' 생성기
    sents = [s.strip() for s in txt.replace("?", ".").split(".") if s.strip()]
    return ". ".join(sents[:max(1, min(n_sent, len(sents)))]) + ("." if sents else "")

def make_items(n: int, seed: int = 42):
    random.seed(seed)
    items = []
    n_half = n // 2

    for i in range(n_half):
        src = random.choice(KO_SOURCES)
        domain = "summarization" if src[0] == "요약" else "qa"
        base = src[1]
        rep = random.choice([1, 2, 3])
        text = " ".join([base] * rep)
        ref = shortify(base, n_sent=2) if domain == "summarization" else "서울"
        item_id = f"KO_{i:04d}"
        items.append(Item(
            id=item_id, input=text, reference=ref, domain=domain, lang="ko",
            diff_bin=random.choice(["easy","normal","hard"]),
            cluster_id=item_id if rep==1 else f"KO_CLUSTER_{i:04d}"
        ))

    for i in range(n - n_half):
        src = random.choice(EN_SOURCES)
        domain = "summarization" if src[0] == "summarization" else "qa"
        base = src[1]
        rep = random.choice([1, 2, 3])
        text = " ".join([base] * rep)
        ref = shortify(base, n_sent=2) if domain == "summarization" else "Seoul"
        item_id = f"EN_{i:04d}"
        items.append(Item(
            id=item_id, input=text, reference=ref, domain=domain, lang="en",
            diff_bin=random.choice(["easy","normal","hard"]),
            cluster_id=item_id if rep==1 else f"EN_CLUSTER_{i:04d}"
        ))
    return items

def write_jsonl(path: Path, objs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="생성할 아이템 수")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    items = make_items(args.n, args.seed)

    prompts = [{"id":it.id, "input":it.input, "domain":it.domain, "lang":it.lang,
                "diff_bin":it.diff_bin, "cluster_id":it.cluster_id} for it in items]
    refs    = [{"id":it.id, "reference":it.reference} for it in items]
    meta    = [{"id":it.id, "domain":it.domain, "lang":it.lang,
                "diff_bin":it.diff_bin, "cluster_id":it.cluster_id} for it in items]

    write_jsonl(Path("data/raw/prompts/prompts.jsonl"), prompts)
    write_jsonl(Path("data/raw/references/references.jsonl"), refs)
    write_jsonl(Path("data/raw/metadata/meta.jsonl"), meta)

    print(f"[seed] wrote {len(items)} items to data/raw/ (prompts/references/metadata)")

if __name__ == "__main__":
    main()