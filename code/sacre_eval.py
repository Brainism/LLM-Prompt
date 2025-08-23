import argparse, json, sys
from pathlib import Path

def read_lines(p: Path):
    return [ln.rstrip("\n") for ln in p.read_text(encoding="utf-8").splitlines()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", required=True)
    ap.add_argument("--hyps-general", required=True)
    ap.add_argument("--hyps-instructed", required=True)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--out-bleu", required=True)
    ap.add_argument("--out-chrf", required=True)
    ap.add_argument("--out-rouge", required=True)
    args = ap.parse_args()

    refs = read_lines(Path(args.refs))
    g    = read_lines(Path(args.hyps_general))
    i    = read_lines(Path(args.hyps_instructed))
    n = min(len(refs), len(g), len(i))
    refs, g, i = refs[:n], g[:n], i[:n]
    ids = [f"ex-{k+1:04d}" for k in range(n)]
    if args.ids and Path(args.ids).exists():
        ids = read_lines(Path(args.ids))[:n]

    from sacrebleu.metrics import BLEU, CHRF
    bleu = BLEU(effective_order=True)
    chrf = CHRF()

    from rouge_score import rouge_scorer
    rsc = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    def per_item_scores(hyps):
        bleu_s, chrf_s, rouge_s = [], [], []
        for hyp, ref in zip(hyps, refs):
            bleu_s.append(float(bleu.sentence_score(hyp, [ref]).score))
            chrf_s.append(float(chrf.sentence_score(hyp, [ref]).score))
            rouge_s.append(float(rsc.score(ref, hyp)["rougeL"].fmeasure * 100.0))
        return bleu_s, chrf_s, rouge_s

    g_bleu, g_chrf, g_rouge = per_item_scores(g)
    i_bleu, i_chrf, i_rouge = per_item_scores(i)

    def pack(metric_name, g_scores, i_scores):
        items = []
        for k in range(n):
            items.append({
                "id": ids[k],
                "general": g_scores[k],
                "instructed": i_scores[k],
                "diff": i_scores[k] - g_scores[k]
            })
        corpus = {
            "general": float(sum(g_scores)/n) if n else 0.0,
            "instructed": float(sum(i_scores)/n) if n else 0.0,
            "diff": float(sum(i_scores)/n - sum(g_scores)/n)
        }
        return {"metric": metric_name, "n": n, "items": items, "corpus": corpus}

    Path(args.out_bleu).write_text(json.dumps(pack("bleu", g_bleu, i_bleu), indent=2), encoding="utf-8")
    Path(args.out_chrf).write_text(json.dumps(pack("chrf", g_chrf, i_chrf), indent=2), encoding="utf-8")
    Path(args.out_rouge).write_text(json.dumps(pack("rougeL", g_rouge, i_rouge), indent=2), encoding="utf-8")
    print("[OK] wrote:", args.out_bleu, args.out_chrf, args.out_rouge)

if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError as e:
        print("필요 패키지 설치:", "python -m pip install sacrebleu rouge-score", file=sys.stderr)
        raise
