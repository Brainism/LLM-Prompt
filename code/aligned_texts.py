import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts" / "prompts.csv"
RAW = ROOT / "results" / "raw"
ALN = ROOT / "results" / "aligned"
QNT = ROOT / "results" / "quantitative"


def die(msg):
    print(f"[ERR] {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_jsonl(fp: Path):
    for line in fp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


def pick_id(rec: dict):
    for k in ("id", "item_id", "example_id"):
        if k in rec:
            return rec[k]
    meta = rec.get("meta")
    if isinstance(meta, dict):
        for k in ("id", "item_id"):
            if k in meta:
                return meta[k]
    return None


def pick_text(rec: dict):
    for k in ("output", "text", "generation", "answer", "content", "response"):
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v
    ch = rec.get("choices")
    if isinstance(ch, list) and ch and isinstance(ch[0], dict):
        v = ch[0].get("text") or (ch[0].get("message") or {}).get("content")
        if isinstance(v, str):
            return v
    return ""


def find_raw_file(kind: str) -> Path:
    """
    kind: 'general' or 'instructed'
    """
    cand = []
    for fp in RAW.glob("*.jsonl"):
        name = fp.name.lower()
        if kind == "general" and ("general" in name) and ("instruct" not in name):
            return fp
        if kind == "instructed" and ("instruct" in name):
            return fp
        cand.append(fp)
    return (
        sorted(cand, key=lambda p: p.stat().st_mtime, reverse=True)[0] if cand else None
    )


def main():
    if not PROMPTS.exists():
        die(f"프롬프트 CSV가 없습니다: {PROMPTS}")
    ALN.mkdir(parents=True, exist_ok=True)
    QNT.mkdir(parents=True, exist_ok=True)

    order, refs = [], {}
    with PROMPTS.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            _id = row["id"]
            order.append(_id)
            refs[_id] = row.get("reference", "")

    g_fp = find_raw_file("general")
    i_fp = find_raw_file("instructed")
    if not g_fp or not i_fp:
        die(
            f"raw 로그를 찾지 못했습니다. (general={g_fp}, instructed={i_fp})  results/raw/*.jsonl 확인"
        )

    def build_out_map(fp: Path):
        m = {}
        for rec in load_jsonl(fp):
            _id = pick_id(rec)
            if not _id:
                continue
            m[_id] = pick_text(rec)
        return m

    out_g = build_out_map(g_fp)
    out_i = build_out_map(i_fp)

    (ALN / "ids.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
    (ALN / "refs.txt").write_text(
        "\n".join(refs[_id] for _id in order) + "\n", encoding="utf-8"
    )
    (ALN / "general.txt").write_text(
        "\n".join(out_g.get(_id, "") for _id in order) + "\n", encoding="utf-8"
    )
    (ALN / "instructed.txt").write_text(
        "\n".join(out_i.get(_id, "") for _id in order) + "\n", encoding="utf-8"
    )

    print("[OK] wrote aligned files to", ALN)

    sacre = ROOT / "code" / "sacre_eval.py"
    if sacre.exists():
        print("[run] sacre_eval.py …")
        subprocess.run(
            [
                sys.executable,
                str(sacre),
                "--refs",
                str((ALN / "refs.txt").relative_to(ROOT)),
                "--hyps-general",
                str((ALN / "general.txt").relative_to(ROOT)),
                "--hyps-instructed",
                str((ALN / "instructed.txt").relative_to(ROOT)),
                "--out-bleu",
                str((QNT / "bleu_sacre.json").relative_to(ROOT)),
                "--out-chrf",
                str((QNT / "chrf.json").relative_to(ROOT)),
                "--out-rouge",
                str((QNT / "rouge.json").relative_to(ROOT)),
            ],
            cwd=ROOT,
            check=False,
        )
    else:
        print("[note] code/sacre_eval.py 가 없어 자동 평가는 건너뜀")


if __name__ == "__main__":
    main()
