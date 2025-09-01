from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_rouge = None


def _ensure_rouge():
    global _rouge
    if _rouge is None:
        from rouge_score import rouge_scorer

        _rouge = rouge_scorer.RougeScorer(
            ["rouge1", "rouge2", "rougeL"], use_stemmer=True
        )
    return _rouge


def _ensure_bertscore():
    try:
        from bert_score import score as bscore

        return bscore
    except Exception:
        return None


try:
    import jsonschema
except Exception:
    jsonschema = None


def normalize_text(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def compute_rouge(pred: str, ref: str) -> Dict[str, float]:
    scorer = _ensure_rouge()
    res = scorer.score(ref, pred)
    return {
        "rouge1_f": float(res["rouge1"].fmeasure),
        "rouge2_f": float(res["rouge2"].fmeasure),
        "rougeL_f": float(res["rougeL"].fmeasure),
    }


def compute_bertscore(
    preds: List[str], refs: List[str], lang_hint: Optional[str] = "multi"
) -> Dict[str, List[float]]:
    bscore = _ensure_bertscore()
    if bscore is None:
        raise RuntimeError(
            "bert-score not available. Install with: pip install bert-score (and torch)."
        )
    model_type = (
        "xlm-roberta-large" if lang_hint in ("multi", "ko", "en", "mixed") else None
    )
    P, R, F1 = bscore(
        preds, refs, model_type=model_type, verbose=False, rescale_with_baseline=False
    )
    return {"bertscore_f1": [float(x) for x in F1.tolist()]}


def compute_bertscore_grouped(
    preds: List[str], refs: List[str], langs: List[str]
) -> Dict[str, List[Optional[float]]]:
    bscore = _ensure_bertscore()
    if bscore is None:
        raise RuntimeError(
            "bert-score not available. Install with: pip install bert-score (and torch)."
        )

    assert len(preds) == len(refs) == len(langs), "preds/refs/langs length mismatch"

    def norm_lang(x: Optional[str]) -> str:
        if not x:
            return "en"
        x = x.lower()
        if x.startswith("ko"):
            return "ko"
        if x.startswith("en"):
            return "en"
        return "other"

    groups = defaultdict(list)
    for i, lg in enumerate(langs):
        groups[norm_lang(lg)].append(i)

    f1_all: List[Optional[float]] = [None] * len(preds)
    model_type = "xlm-roberta-large"

    for lg, idxs in groups.items():
        sub_preds = [preds[i] for i in idxs]
        sub_refs = [refs[i] for i in idxs]
        try:
            if lg in ("ko", "en"):
                P, R, F1 = bscore(
                    sub_preds,
                    sub_refs,
                    model_type=model_type,
                    verbose=False,
                    rescale_with_baseline=False,
                    lang=lg,
                )
            else:
                P, R, F1 = bscore(
                    sub_preds,
                    sub_refs,
                    model_type=model_type,
                    verbose=False,
                    rescale_with_baseline=False,
                )
            for off, i in enumerate(idxs):
                f1_all[i] = float(F1[off])
        except Exception:
            for i in idxs:
                f1_all[i] = None

    return {"bertscore_f1": f1_all}


def try_extract_json(text: str) -> Tuple[Optional[dict], str]:
    cand = text.strip()
    m = re.search(r"\{.*\}", cand, re.DOTALL)
    if m:
        cand = m.group(0)
    try:
        return json.loads(cand), ""
    except Exception as e:
        return None, str(e)


def validate_json_against_schema(
    obj: dict, schema_path: Path
) -> Tuple[bool, int, int, str]:
    if jsonschema is None:
        return False, 0, 0, "jsonschema_not_installed"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        required = schema.get("required", [])
        present = sum(1 for k in required if k in obj and str(obj[k]).strip() != "")
        jsonschema.validate(instance=obj, schema=schema)
        return True, present, len(required), ""
    except jsonschema.exceptions.ValidationError as e:
        required = schema.get("required", []) if "schema" in locals() else []
        present = sum(1 for k in required if k in obj and str(obj[k]).strip() != "")
        return False, present, len(required), str(e)
    except Exception as e:
        required = schema.get("required", []) if "schema" in locals() else []
        present = sum(1 for k in required if k in obj and str(obj[k]).strip() != "")
        return False, present, len(required), str(e)


def scan_forbidden(text: str, terms: List[str]) -> bool:
    low = text.lower()
    return any(t and t.lower() in low for t in terms)


def p50_p95(xs: List[float]) -> Tuple[Optional[float], Optional[float]]:
    if not xs:
        return None, None
    xs_sorted = sorted(xs)

    def pct(p):
        k = (len(xs_sorted) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return xs_sorted[int(k)]
        return xs_sorted[f] + (xs_sorted[c] - xs_sorted[f]) * (k - f)

    return pct(0.5), pct(0.95)
