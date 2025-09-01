from __future__ import annotations

import json
import re


def parse_params(s: str) -> dict[str, str]:
    out = {}
    for tok in (s or "").split(";"):
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def check_format_json(text: str, params: dict) -> tuple[bool, str]:
    try:
        obj = json.loads(text)
    except Exception:
        return False, "json_parse_fail"
    req = set((params.get("keys") or "").split("|"))
    req = {k for k in req if k}
    if req and set(obj.keys()) != req:
        return (
            False,
            f"json_keys_mismatch(expected={sorted(req)}, got={sorted(obj.keys())})",
        )
    return True, "ok"


def check_limit_words(text: str, params: dict) -> tuple[bool, str]:
    try:
        n = int(params.get("words", "0"))
    except:
        n = 0
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    return (len(words) == n, f"words={len(words)} expected={n}")


def check_bullets(text: str, params: dict) -> tuple[bool, str]:
    try:
        n = int(params.get("bullets", "0"))
    except:
        n = 0
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    ok = [ln for ln in lines if ln.startswith("- ")]
    if len(lines) != len(ok):
        return False, "non_bullet_lines_present"
    return (len(ok) == n, f"bullets={len(ok)} expected={n}")


def check_forbid_terms(text: str, params: dict) -> tuple[bool, str]:
    if params.get("forbid") == "digits":
        return (re.search(r"[0-9]", text) is None, "digits_forbidden")
    return True, "ok"


def evaluate_item(scenario: str, text: str, params: dict) -> tuple[bool, str]:
    if scenario == "format-json":
        return check_format_json(text, params)
    if scenario == "limit-words":
        return check_limit_words(text, params)
    if scenario == "bullets":
        return check_bullets(text, params)
    if scenario == "forbid-terms":
        return check_forbid_terms(text, params)
    if scenario == "limit-items-json":
        return check_limit_items_json(text, params)
    if scenario == "limit-chars":
        return check_limit_chars(text, params)
    return False, "unknown_scenario"


def check_limit_items_json(text: str, params: dict) -> tuple[bool, str]:
    import json

    try:
        n = int(params.get("n", "0"))
    except:
        n = 0
    try:
        obj = json.loads(text)
    except Exception:
        return False, "json_parse_fail"
    if not isinstance(obj, list):
        return False, "not_json_list"
    if len(obj) != n:
        return False, f"list_len={len(obj)} expected={n}"
    # 각 항목은 문자열, (옵션) 공백 금지
    no_space = str(params.get("no_space", "false")).lower() == "true"
    for i, el in enumerate(obj):
        if not isinstance(el, str):
            return False, f"elem_{i}_not_string"
        if no_space and any(ch.isspace() for ch in el):
            return False, f"elem_{i}_has_space"
    return True, "ok"


def check_limit_chars(text: str, params: dict) -> tuple[bool, str]:
    mode = str(params.get("mode", "nonspace")).lower()  # nonspace|all
    try:
        n = int(params.get("chars", "0"))
    except:
        n = 0
    t = text if mode == "all" else "".join(ch for ch in text if not ch.isspace())
    return (len(t) == n, f"chars={len(t)} expected={n} mode={mode}")
