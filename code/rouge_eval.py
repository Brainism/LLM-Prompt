#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def read_reference(path: str) -> dict[str, str]:
    ref: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        ref[str(obj["id"])] = str(obj["reference_text"])
    return ref


def lcs_len(a: list[str], b: list[str]) -> int:
    n, m = len(a), len(b)
    dp = [0] * (m + 1)
    for i in range(1, n + 1):
        prev = 0
        for j in range(1, m + 1):
            tmp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = tmp
    return dp[m]


def rouge_l_pair(ref: str, cand: str) -> dict[str, float]:
    rt = ref.split()
    ct = cand.split()
    if not rt or not ct:
        return {"p": 0.0, "r": 0.0, "f": 0.0}
    lcs = lcs_len(rt, ct)
    p = lcs / len(ct)
    r = lcs / len(rt)
    f = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    return {"p": p, "r": r, "f": f}


def load_outputs(dirpath: str) -> list[dict]:
    items = []
    for p in Path(dirpath).glob("*.json"):
        obj = json.loads(p.read_text(encoding="utf-8"))
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
        sc = rouge_l_pair(gt, hyp)
        per_item.append(
            {
                "id": sid,
                "prompt_type": grp,
                "rougeL_p": sc["p"],
                "rougeL_r": sc["r"],
                "rougeL_f": sc["f"],
            }
        )
        by_group[grp].append(sc["f"])

    summary = {
        "overall_mean_f": (sum(x["rougeL_f"] for x in per_item) / max(len(per_item), 1))
        if per_item
        else 0.0,
        "group_mean_f": {k: (sum(v) / max(len(v), 1)) for k, v in by_group.items()},
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(
            {"per_item": per_item, "summary": summary}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    print(f"[OK] ROUGE-L -> {out_path}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--inputs", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument("--output", required=True)
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    evaluate(a.inputs, a.reference, a.output)
