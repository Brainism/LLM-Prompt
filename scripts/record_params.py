import argparse
import random
from pathlib import Path

import numpy as np
import yaml


def main(out, seed, temperature, top_p, max_tokens):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    np.random.seed(seed)
    data = {
        "seed": int(seed),
        "sampling": {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
        },
    }
    Path(out).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"[record_params] wrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="configs/baseline_params.yaml")
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--temperature", required=True, type=float)
    ap.add_argument("--top_p", required=True, type=float)
    ap.add_argument("--max_tokens", required=True, type=int)
    args = ap.parse_args()
    main(**vars(args))
