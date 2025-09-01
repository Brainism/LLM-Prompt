from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path


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
    (
        "?붿빟",
        "?멸났吏??紐⑤뜽? ?ㅼ뼇???꾨찓?몄뿉???쒖슜?섍퀬 ?덈떎. 理쒓렐?먮뒗 ?꾨＼?꾪듃 ?붿??덉뼱留곸씠 ?깅뒫??留ㅼ슦 ???곹뼢??誘몄튇?ㅻ뒗 ?먯씠 諛앺?議뚮떎. 蹂?臾몄꽌???꾨＼?꾪듃 ?ㅺ퀎 ?먯튃怨??됯? 諛⑸쾿??媛꾨떒???뺣━?쒕떎. ?먰븳 ?ы쁽?깃낵 ?듦퀎 寃?뺤쓽 以묒슂?깆쓣 媛뺤“?쒕떎.",
    ),
    (
        "?붿빟",
        "?곗씠???꾩쿂由щ뒗 紐⑤뜽 ?깅뒫??湲곕컲?대떎. ?띿뒪???뺢퇋?? ?좏겙??洹쒖튃, 湲덉튃?? JSON ?ㅽ궎留?以???깆? ?쇨??곸쑝濡?愿由щ릺?댁빞 ?쒕떎. ??媛?대뱶???ㅻТ ?섍꼍?먯꽌 ?뷀엳 諛쒖깮?섎뒗 ?ㅻ쪟瑜?以꾩씠湲??꾪븳 泥댄겕由ъ뒪?몃? ?쒓났?쒕떎.",
    ),
    (
        "QA",
        "??쒕?援?쓽 ?섎룄???대뵒?멸?? 諛곌꼍吏?앹뿉 ?곕Ⅴ硫??쒖슱?밸퀎?쒓? ?됱젙?섎룄 ??븷???섑뻾?섍퀬 ?덈떎.",
    ),
]
EN_SOURCES = [
    (
        "summarization",
        "Large language models are increasingly used across domains. Prompt design substantially influences outcomes. This note outlines prompt principles, evaluation metrics, reproducibility, and statistical testing.",
    ),
    (
        "summarization",
        "Data preprocessing underpins model performance. Normalization, tokenization, forbidden terms, and JSON schema compliance should be enforced consistently to reduce common production errors.",
    ),
    (
        "qa",
        "What is the capital of South Korea? Based on background knowledge, Seoul is the administrative capital.",
    ),
]


def shortify(txt: str, n_sent: int = 2) -> str:
    # 留ㅼ슦 ?⑥닚??'?덊띁?곗뒪 ?붿빟' ?앹꽦湲?
    sents = [s.strip() for s in txt.replace("?", ".").split(".") if s.strip()]
    return ". ".join(sents[: max(1, min(n_sent, len(sents)))]) + ("." if sents else "")


def make_items(n: int, seed: int = 42):
    random.seed(seed)
    items = []
    n_half = n // 2

    for i in range(n_half):
        src = random.choice(KO_SOURCES)
        domain = "summarization" if src[0] == "?붿빟" else "qa"
        base = src[1]
        rep = random.choice([1, 2, 3])
        text = " ".join([base] * rep)
        ref = shortify(base, n_sent=2) if domain == "summarization" else "?쒖슱"
        item_id = f"KO_{i:04d}"
        items.append(
            Item(
                id=item_id,
                input=text,
                reference=ref,
                domain=domain,
                lang="ko",
                diff_bin=random.choice(["easy", "normal", "hard"]),
                cluster_id=item_id if rep == 1 else f"KO_CLUSTER_{i:04d}",
            )
        )

    for i in range(n - n_half):
        src = random.choice(EN_SOURCES)
        domain = "summarization" if src[0] == "summarization" else "qa"
        base = src[1]
        rep = random.choice([1, 2, 3])
        text = " ".join([base] * rep)
        ref = shortify(base, n_sent=2) if domain == "summarization" else "Seoul"
        item_id = f"EN_{i:04d}"
        items.append(
            Item(
                id=item_id,
                input=text,
                reference=ref,
                domain=domain,
                lang="en",
                diff_bin=random.choice(["easy", "normal", "hard"]),
                cluster_id=item_id if rep == 1 else f"EN_CLUSTER_{i:04d}",
            )
        )
    return items


def write_jsonl(path: Path, objs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for o in objs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="?앹꽦???꾩씠????)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    items = make_items(args.n, args.seed)

    prompts = [
        {
            "id": it.id,
            "input": it.input,
            "domain": it.domain,
            "lang": it.lang,
            "diff_bin": it.diff_bin,
            "cluster_id": it.cluster_id,
        }
        for it in items
    ]
    refs = [{"id": it.id, "reference": it.reference} for it in items]
    meta = [
        {
            "id": it.id,
            "domain": it.domain,
            "lang": it.lang,
            "diff_bin": it.diff_bin,
            "cluster_id": it.cluster_id,
        }
        for it in items
    ]

    write_jsonl(Path("data/raw/prompts/prompts.jsonl"), prompts)
    write_jsonl(Path("data/raw/references/references.jsonl"), refs)
    write_jsonl(Path("data/raw/metadata/meta.jsonl"), meta)

    print(f"[seed] wrote {len(items)} items to data/raw/ (prompts/references/metadata)")


if __name__ == "__main__":
    main()
