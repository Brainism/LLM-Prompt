from __future__ import annotations
import argparse, json
from pathlib import Path
import sacrebleu

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", required=True)
    ap.add_argument("--hyps-general", required=True)
    ap.add_argument("--hyps-instructed", required=True)
    ap.add_argument("--out-bleu", required=True)
    ap.add_argument("--out-chrf", required=True)
    args = ap.parse_args()

    refs = [ln.rstrip("\n") for ln in open(args.refs, encoding="utf-8")]
    g    = [ln.rstrip("\n") for ln in open(args.hyps_general, encoding="utf-8")]
    i    = [ln.rstrip("\n") for ln in open(args.hyps_instructed, encoding="utf-8")]
    if not (len(refs) == len(g) == len(i)):
        raise SystemExit("refs/general/instructed 길이가 다릅니다.")

    bleu_g = sacrebleu.corpus_bleu(g, [refs])
    bleu_i = sacrebleu.corpus_bleu(i, [refs])
    chrf_m = sacrebleu.CHRF()
    chrf_g = chrf_m.corpus_score(g, [refs])
    chrf_i = chrf_m.corpus_score(i, [refs])

    items_bleu = []
    items_chrf = []
    for idx, (r, hg, hi) in enumerate(zip(refs, g, i), 1):
        sb_g = sacrebleu.sentence_bleu(hg, [r]).score
        sb_i = sacrebleu.sentence_bleu(hi, [r]).score
        sc_g = chrf_m.sentence_score(hg, [r]).score
        sc_i = chrf_m.sentence_score(hi, [r]).score
        items_bleu.append({"id": str(idx), "general": sb_g/100.0, "instructed": sb_i/100.0})
        items_chrf.append({"id": str(idx), "general": sc_g/100.0, "instructed": sc_i/100.0})

    Path(args.out_bleu).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_chrf).parent.mkdir(parents=True, exist_ok=True)
    sig = getattr(bleu_g, "signature", None)
    with open(args.out_bleu, "w", encoding="utf-8") as f:
        json.dump({
            "metric": "bleu_sacre",
            "items": items_bleu,
            "corpus": {"general": bleu_g.score/100.0, "instructed": bleu_i.score/100.0},
            **({"signature": str(sig)} if sig is not None else {})
        }, f, ensure_ascii=False, indent=2)
    with open(args.out_chrf, "w", encoding="utf-8") as f:
        json.dump({
            "metric": "chrf",
            "items": items_chrf,
            "corpus": {"general": chrf_g.score/100.0, "instructed": chrf_i.score/100.0}
        }, f, ensure_ascii=False, indent=2)
    print("[OK] sacreBLEU/chrF ->", args.out_bleu, ",", args.out_chrf)

if __name__ == "__main__":
    main()
