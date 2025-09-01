import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
MANI = ROOT / "data" / "manifest" / "split_manifest_main.json"
PROMPTS = ROOT / "prompts" / "prompts.csv"
RAW = ROOT / "results" / "raw"
QNT = ROOT / "results" / "quantitative"
ALN = ROOT / "results" / "aligned"

PROVIDER = "ollama"
MODEL_GENERAL = "gemma:7b"
MODEL_INSTRUCT = "gemma:7b-instruct"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def log(*a):
    print("[run]", *a)


def run_cmd(args, cwd=ROOT):
    log(" ".join(str(x) for x in args))
    r = subprocess.run(args, cwd=cwd)
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def ensure_dirs():
    for p in (RAW, QNT, ALN, PROMPTS.parent):
        p.mkdir(parents=True, exist_ok=True)


def ollama_alive():
    try:
        req = Request(OLLAMA_HOST + "/api/tags", headers={"Accept": "application/json"})
        with urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_ollama_models():
    def has_model(name):
        try:
            req = Request(
                OLLAMA_HOST + "/api/tags", headers={"Accept": "application/json"}
            )
            with urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
            return any(
                t.get("name") == name for t in data.get("models", data.get("tags", []))
            )
        except Exception:
            return False

    for m in (MODEL_GENERAL, MODEL_INSTRUCT):
        if not has_model(m):
            log(f"紐⑤뜽 ?놁쓬 ??pull: {m}")
            run_cmd(["ollama", "pull", m])


def ensure_prompts_csv():
    if PROMPTS.exists():
        return
    if not MANI.exists():
        raise FileNotFoundError(f"留ㅻ땲?섏뒪?멸? ?놁뒿?덈떎: {MANI}")
    data = json.loads(MANI.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        raise SystemExit("留ㅻ땲?섏뒪??items媛 鍮꾩뼱 ?덉뒿?덈떎.")
    with PROMPTS.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "input",
                "reference",
                "domain",
                "lang",
                "len_bin",
                "diff_bin",
                "cluster_id",
            ]
        )
        for it in items:
            w.writerow(
                [
                    it["id"],
                    it["input"],
                    it["reference"],
                    it["domain"],
                    it["lang"],
                    it["len_bin"],
                    it["diff_bin"],
                    it["cluster_id"],
                ]
            )
    log(f"?앹꽦 ?꾨즺: {PROMPTS} (n={len(items)})")


def aggregate_efficiency():
    recs = []
    for fp in RAW.glob("*.jsonl"):
        for ln in fp.read_text(encoding="utf-8").splitlines():
            try:
                recs.append(json.loads(ln))
            except Exception:
                pass
    lat = np.array([float(r.get("latency_ms", 0.0)) for r in recs], dtype=float)
    cost = np.array([float(r.get("cost_usd", 0.0)) for r in recs], dtype=float)
    tile = {
        "latency_ms_p50": float(np.percentile(lat, 50)) if lat.size else None,
        "latency_ms_p95": float(np.percentile(lat, 95)) if lat.size else None,
        "cost_usd_p50": float(np.percentile(cost, 50)) if cost.size else None,
        "cost_usd_p95": float(np.percentile(cost, 95)) if cost.size else None,
        "n": len(recs),
    }
    out = QNT / "efficiency_tile.json"
    out.write_text(json.dumps(tile, indent=2), encoding="utf-8")
    log("efficiency tile ??, out)


def main():
    ensure_dirs()
    if not ollama_alive():
        raise SystemExit(
            "Ollama ?쒕쾭???곌껐?????놁뒿?덈떎.\n"
            f"- 湲곕? 二쇱냼: {OLLAMA_HOST}\n"
            "- Ollama Desktop ?먮뒗 `ollama serve` 瑜??ㅽ뻾?섏꽭??\n"
        )
    ensure_ollama_models()
    ensure_prompts_csv()

    run_cmd(
        [
            sys.executable,
            str(CODE / "run_langchain_experiment.py"),
            "--prompt-file",
            str(PROMPTS.relative_to(ROOT)),
            "--prompt-column",
            "input",
            "--id-column",
            "id",
            "--mode",
            "general",
            "--outdir",
            str(RAW.relative_to(ROOT)),
            "--provider",
            PROVIDER,
            "--model",
            MODEL_GENERAL,
        ]
    )

    run_cmd(
        [
            sys.executable,
            str(CODE / "run_langchain_experiment.py"),
            "--prompt-file",
            str(PROMPTS.relative_to(ROOT)),
            "--prompt-column",
            "input",
            "--id-column",
            "id",
            "--mode",
            "instructed",
            "--outdir",
            str(RAW.relative_to(ROOT)),
            "--provider",
            PROVIDER,
            "--model",
            MODEL_INSTRUCT,
        ]
    )

    run_cmd([sys.executable, str(CODE / "aligned_texts.py")])

    stats_plus = CODE / "stats_tests_plus.py"
    stats_uni = CODE / "stats_tests_unified.py"
    stats_py = stats_plus if stats_plus.exists() else stats_uni
    if not stats_py.exists():
        raise SystemExit(
            "?듦퀎 ?ㅽ겕由쏀듃瑜?李얠쓣 ???놁뒿?덈떎: stats_tests_plus.py ?먮뒗 stats_tests_unified.py"
        )
    run_cmd(
        [
            sys.executable,
            str(stats_py),
            "--bleu",
            str((QNT / "bleu_sacre.json").relative_to(ROOT)),
            "--chrf",
            str((QNT / "chrf.json").relative_to(ROOT)),
            "--rouge",
            str((QNT / "rouge.json").relative_to(ROOT)),
            "--output",
            str((QNT / "stats_summary.csv").relative_to(ROOT)),
            "--bootstrap",
            "10000",
            "--wilcoxon",
            "--fdr",
        ]
    )

    try:
        aggregate_efficiency()
    except Exception as e:
        log("?⑥쑉 ???怨꾩궛 ?ㅽ뙣(嫄대꼫?):", e)

    log("?럦 ?꾨즺: raw/aligned/quantitative ?곗텧臾??앹꽦")


if __name__ == "__main__":
    main()
