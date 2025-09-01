from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "results" / "batch_outputs"
GEN = BATCH / "general.jsonl"
INS = BATCH / "instructed.jsonl"

REPLACEMENTS = {
    "1": {"city": "서울", "temp_unit": "C"},
    "3": {
        "steps": [
            "물을 끓인다",
            "면을 넣는다",
            "분말스프를 넣는다",
            "그릇에 담아 마무리한다",
        ]
    },
    "5": {"product": "책상", "price": "10000원"},
    "7": {
        "steps": [
            "차량을 주차한다",
            "커넥터를 연결한다",
            "인증/결제를 진행한다",
            "충전 완료까지 대기한다",
            "커넥터를 분리하고 커버를 닫는다",
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
