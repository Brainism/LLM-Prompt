from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

POSS_KEYS = ["output_text", "text", "output", "generation"]


def read_reference(path: str) -> dict[str, str]:
    ref = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        ref[str(obj["id"])] = str(obj["reference_text"])
    return ref


def ngrams(tokens: list[str], n: int) -> Counter:
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def bleu4(ref: str, cand: str) -> float:
    rt = ref.split()
    ct = cand.split()
    if len(ct) == 0:
        return 0.0
    bp = 1.0 if len(ct) >= len(rt) else math.exp(1 - len(rt) / max(len(ct), 1))
    log_sum = 0.0
    for n in range(1, 5):
        c_ngr = ngrams(ct, n)
        r_ngr = ngrams(rt, n)
        overlap = sum(min(c_ngr[g], r_ngr[g]) for g in c_ngr)
        prec = (overlap + 1) / (sum(c_ngr.values()) + 1)
        log_sum += math.log(prec)
    geo = math.exp(log_sum / 4.0)
    return bp * geo


def load_outputs(dirpath: str) -> list[dict]:
    items = []
    for p in Path(dirpath).glob("*.json"):
        obj = json.loads(p.read_text(encoding="utf-8"))
        for k in POSS_KEYS:
            if k in obj:
                obj["output_text"] = obj[k]
                break
        items.append(obj)
    return items


def evaluate(inputs_dir: str, reference_path: str, out_path: str) -> None:
    ref = read_reference(reference_path)
    outs = load_outputs(inputs_dir)
    per_item = []
    by_group = defaultdict(list)
    for o in outs:
        sid = str(o.get("id"))
        hyp = str(o.get("output_text", ""))
        grp = str(o.get("prompt_type", "unknown"))
        gt = ref.get(sid, "")
        score = bleu4(gt, hyp)
        per_item.append({"id": sid, "prompt_type": grp, "bleu4": score})
        by_group[grp].append(score)
    summary = {
        "overall_mean_bleu4": sum([x["bleu4"] for x in per_item])
        / max(len(per_item), 1),
        "group_mean_bleu4": {k: (sum(v) / max(len(v), 1)) for k, v in by_group.items()},
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(
            {"per_item": per_item, "summary": summary}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    print(f"[OK] CodeBLEU-proxy (BLEU-4) -> {out_path}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    evaluate(a.inputs, a.reference, a.output)
