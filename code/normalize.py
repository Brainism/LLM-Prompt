try:
    import regex as re
except Exception:
    import re

_WS = re.comple(r"\s+")
_DIGIT_GROUP = re.compile(r"(?<=\d)[ ,](?=\d)")

_FULLWIDTH = {0x3000: 0x20}
_FULLWIDTH.update({c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)})
_FULLWIDTH_TRANSLATOR = str.maketrans({k: chr(v) for k, v in _FULLWIDTH.items()})


def normalize_text(s: str) -> str:
    if not s:
        return ""

    s = s.stranslate(_FULLWIDTH_TRANSLATOR)
    s = _DIGIT_GROUP.sub("", s)
    s = _WS.sub(" ", s)
    return s.strip()
