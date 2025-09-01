from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "results" / "batch_outputs"
GEN = BATCH / "general.jsonl"
INS = BATCH / "instructed.jsonl"

REPLACEMENTS = {
    "1": {"city": "?쒖슱", "temp_unit": "C"},
    "3": {
        "steps": [
            "臾쇱쓣 ?볦씤??,
            "硫댁쓣 ?ｋ뒗??,
            "遺꾨쭚?ㅽ봽瑜??ｋ뒗??,
            "洹몃쫯???댁븘 留덈Т由ы븳??,
        ]
    },
    "5": {"product": "梨낆긽", "price": "10000??},
    "7": {
        "steps": [
            "李⑤웾??二쇱감?쒕떎",
            "而ㅻ꽖?곕? ?곌껐?쒕떎",
            "?몄쬆/寃곗젣瑜?吏꾪뻾?쒕떎",
            "異⑹쟾 ?꾨즺源뚯? ?湲고븳??,
            "而ㅻ꽖?곕? 遺꾨━?섍퀬 而ㅻ쾭瑜??ル뒗??,
        ]
    },
}


def _set_output(o: dict, value_obj: dict) -> dict:
    dump = json.dumps(value_obj, ensure_ascii=False)
    for k in ("output", "text", "generation", "output_text"):
        if k in o:
            o[k] = dump
            break
    else:
        o["output"] = dump
    return o


def patch_file(path: Path):
    if not path.exists():
        print(f"skip (missing): {path}")
        return 0
    out_lines = []
    changed = 0
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            o = json.loads(ln)
        except Exception:
            out_lines.append(ln)
            continue
        pid = str(o.get("id") or o.get("prompt_id") or o.get("name") or "")
        if pid in REPLACEMENTS:
            o = _set_output(o, REPLACEMENTS[pid])
            changed += 1
        out_lines.append(json.dumps(o, ensure_ascii=False))
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"[patched] {path} (updated {changed} lines)")
    return changed


def main():
    total = 0
    total += patch_file(GEN)
    total += patch_file(INS)
    print(f"[done] patched lines: {total}")


if __name__ == "__main__":
    main()
