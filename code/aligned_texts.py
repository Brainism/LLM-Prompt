# file: code/aligned_texts.py
from __future__ import annotations
import json, sys, subprocess, re
from pathlib import Path

def _looks_like_root(p: Path) -> bool:
    return ((p / "results" / "batch_outputs").exists()
            or ((p / "results").exists() and (p / "prompts").exists())
            or (p / "code").exists())

def search_root() -> Path:
    start = Path(__file__).resolve().parent
    for p in [start] + list(start.parents):
        if _looks_like_root(p):
            return p
    cwd = Path.cwd()
    for p in [cwd] + list(cwd.parents):
        if _looks_like_root(p):
            return p
    return cwd

def find_first(*cands: Path) -> Path | None:
    for p in cands:
        if p and p.exists():
            return p
    return None

_CB = re.compile(r"^\s*```(?:[\w+-]+)?\s*(.*?)\s*```\s*$", re.DOTALL)

def _unwrap_fence(s: str) -> str:
    m = _CB.match(s or "")
    return m.group(1) if m else (s or "")

def load_jsonl_map(p: Path, text_keys=("output","text","generation","output_text","content","response","completion")) -> dict[str,str]:
    m: dict[str,str] = {}
    with p.open(encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            o = json.loads(ln)
            pid = str(o.get("id") or o.get("prompt_id") or o.get("name"))
            txt = ""
            for k in text_keys:
                if o.get(k) is not None:
                    txt = o[k]; break
            txt = _unwrap_fence(txt)
            m[pid] = (txt or "").replace("\n"," ").strip()
    return m

def load_reference_map(p: Path) -> dict[str,str]:
    pref = ("text","reference","ref","target","expected","gold","answer","output","completion","gt","label",
            "output_text","target_text","reference_text","gold_text","answer_text",
            "ground_truth","groundtruth","gt_text","ideal","solution","canonical","ref_text","expected_output","label_text")
    ignore = {"id","prompt_id","name","scenario","param","limit","meta","tags"}
    m: dict[str,str] = {}
    with p.open(encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            o = json.loads(ln)
            pid = str(o.get("id") or o.get("prompt_id") or o.get("name"))
            txt = None
            for k in pref:
                if k in o:
                    v = o[k]
                    if isinstance(v, str) and v.strip():
                        txt = v; break
                    if isinstance(v, dict):
                        vv = v.get("text") or v.get("value")
                        if isinstance(vv, str) and vv.strip():
                            txt = vv; break
            if txt is None:
                for k,v in o.items():
                    if k in ignore: continue
                    if isinstance(v, str) and v.strip():
                        txt = v; break
                    if isinstance(v, dict):
                        vv = v.get("text") or v.get("value")
                        if isinstance(vv, str) and vv.strip():
                            txt = vv; break
            txt = _unwrap_fence(txt or "")
            m[pid] = (txt or "").replace("\n"," ").strip()
    return m

def _gather_items_from_json_dir(d: Path):
    gen, ins = [], []
    for p in sorted(d.glob("*.json")):
        try:
            o = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        pid = str(o.get("id") or o.get("prompt_id") or o.get("name") or p.stem)
        mode = str(o.get("prompt_type") or o.get("mode") or "").lower()
        txt  = o.get("output_text") or o.get("output") or o.get("text") or ""
        item = {"id": pid, "output": (txt or "").replace("\n"," ")}
        if mode.startswith("gen"):
            gen.append(item)
        elif mode.startswith("instr"):
            ins.append(item)
    return gen, ins

def _write_jsonl(path: Path, items: list[dict]):
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

def find_outputs_pair(root: Path) -> tuple[Path, Path]:
    d1 = root / "results" / "batch_outputs"
    d2 = root / "code" / "results" / "batch_outputs"
    for d in [d1, d2]:
        if not d.exists():
            continue
        g = d / "general.jsonl"
        i = d / "instructed.jsonl"
        if g.exists() and i.exists():
            return g, i
        gen_items, ins_items = _gather_items_from_json_dir(d)
        if gen_items and ins_items:
            _write_jsonl(g, gen_items)
            _write_jsonl(i, ins_items)
            print(f"[build] JSON → JSONL: {g.name}, {i.name} (dir={d})")
            return g, i
    rcode = root / "code" / "results"
    if rcode.exists():
        gen_items, ins_items = _gather_items_from_json_dir(rcode)
        if gen_items and ins_items:
            outdir = d1 if d1.exists() else d2 if d2.exists() else rcode
            outdir.mkdir(parents=True, exist_ok=True)
            g, i = outdir / "general.jsonl", outdir / "instructed.jsonl"
            _write_jsonl(g, gen_items)
            _write_jsonl(i, ins_items)
            print(f"[build] code/results/*.json → JSONL: {g}, {i}")
            return g, i
    raise FileNotFoundError("출력 general/instructed를 찾거나 생성할 수 없습니다.")

def main():
    root = search_root()
    ref = find_first(root/"reference"/"reference_corpus.jsonl",
                     root/"data"/"reference_corpus.jsonl",
                     root/"results"/"reference"/"reference_corpus.jsonl")
    if not ref:
        sys.stderr.write("❌ reference_corpus.jsonl 필요\n"); sys.exit(2)
    try:
        gen, ins = find_outputs_pair(root)
    except FileNotFoundError as e:
        sys.stderr.write(f"❌ {e}\n"); sys.exit(2)
    sacre = root/"code"/"sacre_eval.py"
    stats = root/"code"/"stats_tests.py"
    if not sacre.exists():
        sys.stderr.write(f"❌ 없음: {sacre}\n"); sys.exit(2)
    if not stats.exists():
        sys.stderr.write(f"❌ 없음: {stats}\n"); sys.exit(2)
    aligned_dir = root/"results"/"aligned"
    aligned_dir.mkdir(parents=True, exist_ok=True)
    ref_map = load_reference_map(ref)
    gen_map = load_jsonl_map(gen)
    ins_map = load_jsonl_map(ins)
    ids = sorted(set(ref_map) & set(gen_map) & set(ins_map))
    if not ids:
        sys.stderr.write("❌ 공통 id 없음\n"); sys.exit(2)
    refs_txt = aligned_dir/"refs.txt"
    g_txt    = aligned_dir/"hyps_general.txt"
    i_txt    = aligned_dir/"hyps_instructed.txt"
    with refs_txt.open("w", encoding="utf-8") as fr, \
         g_txt.open("w", encoding="utf-8") as fg, \
         i_txt.open("w", encoding="utf-8") as fi:
        for pid in ids:
            fr.write(ref_map[pid] + "\n")
            fg.write(gen_map[pid] + "\n")
            fi.write(ins_map[pid] + "\n")
    print(f"[aligned] wrote {len(ids)} lines -> {aligned_dir}")
    out_bleu = root/"results"/"quantitative"/"bleu_sacre.json"
    out_chrf = root/"results"/"quantitative"/"chrf.json"
    out_bleu.parent.mkdir(parents=True, exist_ok=True)
    cmd_bleu = [sys.executable, str(sacre),
                "--refs", str(refs_txt),
                "--hyps-general", str(g_txt),
                "--hyps-instructed", str(i_txt),
                "--out-bleu", str(out_bleu),
                "--out-chrf", str(out_chrf)]
    print("[sacre] running:", " ".join(cmd_bleu))
    subprocess.run(cmd_bleu, check=True)
    cmd_stats = [sys.executable, str(stats)]
    print("[stats] running:", " ".join(cmd_stats))
    subprocess.run(cmd_stats, check=True)
    print("[OK] BLEU/chrF computed and stats refreshed.")

if __name__ == "__main__":
    main()