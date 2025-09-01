import json
from pathlib import Path


def build_reference_jsonl(out_path: str = "reference/reference_corpus.jsonl") -> None:
    items = [
        {"id": "1", "reference_text": '{"city":"?쒖슱","temp_unit":"C"}'},
        {
            "id": "2",
            "reference_text": "?곗씠???덉쭏? 紐⑤뜽 ?깅뒫怨??좊ː?꾨? ?ш쾶 醫뚯슦?쒕떎",
        },  # ?댁슜? 李멸퀬??
        {"id": "3", "reference_text": "- 臾??볦씠湲?n- 硫??ｊ린\n- ?ㅽ봽 ?ｊ린\n- 遺??꾧린"},
        {"id": "4", "reference_text": "??媛???媛???媛?},
        {"id": "5", "reference_text": '{"product":"梨낆긽","price":"10000??}'},
        {
            "id": "6",
            "reference_text": "?멸났吏???깅뒫? ?곗씠???덉쭏怨?吏??以?섍? 醫뚯슦?쒕떎",
        },  # ?댁슜? 李멸퀬??
        {
            "id": "7",
            "reference_text": "- 耳?대툝 ?곌껐\n- ?몄쬆 ?쒖옉\n- 異⑹쟾 ?쒖옉\n- 異⑹쟾 紐⑤땲?곕쭅\n- 異⑹쟾 醫낅즺",
        },
        {"id": "8", "reference_text": "??媛??ㅻТ 媛??쒕Ⅸ 媛?},
    ]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for obj in items:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"[OK] wrote {len(items)} refs -> {out}")


if __name__ == "__main__":
    build_reference_jsonl()
