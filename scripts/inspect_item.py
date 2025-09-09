from __future__ import annotations
import sys, json, csv, argparse, re
from pathlib import Path
from typing import List, Dict, Any

def load_jsonl(path: Path) -> List[Dict[str,Any]]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception as e:
                print(f"[WARN] skip malformed line in {path}: {e}")
    return out

def load_manifest(man_path: Path) -> Dict[str,str]:
    if not man_path.exists():
        return {}
    try:
        obj = json.loads(man_path.read_text(encoding="utf-8"))
        items = obj.get("items", [])
        return { str(it.get("id")): (it.get("reference") or "") for it in items if it.get("id") is not None }
    except Exception:
        return {}

def load_prompts_csv(csv_path: Path) -> Dict[str,str]:
    if not csv_path.exists():
        return {}
    out = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = (row.get("id") or row.get("ID") or row.get("prompt_id") or "").strip()
            ref = (row.get("reference") or row.get("answer") or "").strip()
            if pid:
                out[pid] = ref
    return out

def norm_text(s: str) -> str:
    if s is None:
        return ""
    s2 = str(s).lower()
    s2 = re.sub(r"[^\w\s]", " ", s2)
    s2 = re.sub(r"\s+", " ", s2).strip()
    return s2

def lcs_len(a: str, b: str) -> int:
    if not a or not b:
        return 0
    A,B = a, b
    la, lb = len(A), len(B)
    dp = [0]*(lb+1)
    for i in range(la):
        prev = 0
        ai = A[i]
        for j in range(lb):
            tmp = dp[j+1]
            if ai == B[j]:
                dp[j+1] = prev + 1
            else:
                if dp[j] > dp[j+1]:
                    dp[j+1] = dp[j]
            prev = tmp
    return dp[lb]

def find_by_id(arr, idkey):
    return [o for o in arr if str(o.get("id") or o.get("prompt_id") or "") == idkey]

def summarize_entry(obj):
    out_text = obj.get("output") or obj.get("text") or obj.get("response") or obj.get("result") or obj.get("out") or ""
    prompt = obj.get("prompt") or obj.get("input") or ""
    return out_text, prompt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="IDs to inspect (e.g. EX-0001). Use --list to show IDs.")
    ap.add_argument("--list", type=int, metavar="N", help="List first N ids found in general.jsonl")
    args = ap.parse_args()

    repo = Path.cwd()
    gen_path = repo / "results" / "raw" / "general.jsonl"
    ins_path = repo / "results" / "raw" / "instructed.jsonl"
    manifest_path = repo / "split_manifest.json"
    prompts_csv = repo / "prompts" / "main.csv"

    gen = load_jsonl(gen_path)
    ins = load_jsonl(ins_path)
    refs = load_manifest(manifest_path)
    csv_refs = load_prompts_csv(prompts_csv)

    if args.list:
        ids_found = []
        for o in gen:
            pid = str(o.get("id") or o.get("prompt_id") or "")
            if pid and pid not in ids_found:
                ids_found.append(pid)
            if len(ids_found) >= args.list:
                break
        print("IDs (first {}): {}".format(args.list, ", ".join(ids_found)))
        return

    if not args.ids:
        print("No IDs provided. Use --list N to list ids, or provide ID(s) to inspect.")
        return

    for idkey in args.ids:
        print("="*80)
        print("ID:", idkey)
        ref = refs.get(idkey, None)
        if ref is None or ref == "":
            ref = csv_refs.get(idkey, "")
            if ref:
                print("[INFO] reference found in prompts/main.csv")
        print("Reference (raw):", repr(ref)[:400])
        ref_norm = norm_text(ref)
        print("Reference (normalized):", repr(ref_norm)[:400])

        g_entries = find_by_id(gen, idkey)
        i_entries = find_by_id(ins, idkey)

        if not g_entries:
            print("[WARN] no general entry found for id in results/raw/general.jsonl")
        if not i_entries:
            print("[WARN] no instructed entry found for id in results/raw/instructed.jsonl")

        def report_side(label, entries):
            if not entries:
                print(f"{label}: NONE")
                return
            for idx,o in enumerate(entries):
                out_text, prompt = summarize_entry(o)
                out_snip = out_text if len(out_text) < 600 else out_text[:600] + " ...[truncated]"
                print(f"--- {label} entry #{idx+1} ---")
                print(" recorded_mode:", o.get("mode"))
                print(" model:", o.get("model"))
                print(" latency_ms:", o.get("latency_ms"))
                print(" prompt (recorded):", repr(prompt)[:500])
                print(" output (raw):", repr(out_snip))
                out_norm = norm_text(out_text)
                contains_ref = False
                lcs_ratio = 0.0
                if ref_norm:
                    contains_ref = (ref_norm in out_norm)
                    lcs = lcs_len(ref_norm, out_norm)
                    lcs_ratio = lcs / max(1, len(ref_norm))
                print(" output (normalized snippet):", repr(out_norm[:300]))
                print(" contains_ref (normalized):", contains_ref)
                print(" lcs_ratio (ref vs out_norm):", round(lcs_ratio,4))
        report_side("GENERAL", g_entries)
        report_side("INSTRUCTED", i_entries)

        if g_entries and i_entries:
            g_out = summarize_entry(g_entries[0])[0]
            i_out = summarize_entry(i_entries[0])[0]
            same = (g_out == i_out)
            print("GENERAL == INSTRUCTED (raw equality):", same)
            if not same:
                print("GENERAL snippet:", repr(g_out[:300]))
                print("INSTRUCTED snippet:", repr(i_out[:300]))
        print("="*80)

if __name__ == "__main__":
    main()