from __future__ import annotations
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

try:
    import requests
except Exception:
    requests = None

DEFAULT_HOST = "http://localhost:11434"


def read_prompts_csv(p: Path) -> List[Dict[str, str]]:
    """Read CSV prompts (utf-8-sig safe). Return list[dict]."""
    with p.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = []
        for row in r:
            rows.append(row)
        return rows


def read_manifest_as_rows(manifest_path: Path) -> List[Dict[str, str]]:
    if not manifest_path.exists():
        raise SystemExit(f"[ERR] manifest not found: {manifest_path}")
    obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = obj.get("items", [])
    rows: List[Dict[str, str]] = []
    for it in items:
        rows.append({
            "id": it.get("id"),
            "input": it.get("input") or it.get("prompt") or "",
            "reference": it.get("reference") or "",
            "system_general": it.get("system_general") or "",
            "system_instructed": it.get("system_instructed") or "",
            "lang": it.get("lang") or "",
            "len_bin": it.get("len_bin") or "",
            "diff_bin": it.get("diff_bin") or ""
        })
    return rows


def build_prompt_text(row: Dict[str, Any], mode: str) -> str:
    body = (row.get("input") or row.get("prompt") or "").strip()
    sys_general = (row.get("system_general") or "").strip()
    sys_instruct = (row.get("system_instructed") or "").strip()

    mode_val = (mode or "").strip().lower()

    if mode_val == "general":
        if sys_general:
            return f"{sys_general}\n\n{body}" if body else sys_general
        return body

    if sys_instruct:
        return f"{sys_instruct}\n\n{body}" if body else sys_instruct

    strong = (
        "You are a strict, concise assistant. "
        "Answer the user's prompt clearly and briefly. "
        "If the prompt asks for a list, provide a numbered list. "
        "If it asks for code, provide runnable code only. "
        "Do not provide extra commentary. "
        "Limit your answer to one or two sentences unless specifically asked for more.\n\n"
    )
    return strong + body


def call_ollama_http(prompt_text: str, model: str, host: str, timeout: int):
    if requests is None:
        raise SystemExit("[ERR] requests not installed. Install with: pip install requests or use --use-cli")
    url = f"{host.rstrip('/')}/api/generate?model={model}"
    headers = {"Content-Type": "application/json"}
    payload = {"prompt": prompt_text}
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"text": resp.text}


def call_ollama_cli(prompt_text: str, model: str, timeout: int):
    candidates = [
        ["ollama", "run", model, "--format", "json", prompt_text],
        ["ollama", "run", model, prompt_text],
        ["ollama", "chat", model, prompt_text],
        ["ollama", "generate", model, prompt_text],
    ]
    last_out = ""
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
        except FileNotFoundError:
            raise FileNotFoundError("ollama CLI not found in PATH (install or remove --use-cli)")
        except subprocess.TimeoutExpired:
            raise

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        last_out = stdout or stderr

        if proc.returncode == 0 and stdout:
            try:
                j = json.loads(stdout)
                if isinstance(j, dict):
                    if "message" in j and isinstance(j["message"], str):
                        return {"text": j["message"]}
                    if "text" in j and isinstance(j["text"], str):
                        return {"text": j["text"]}
                    if "choices" in j and isinstance(j["choices"], list) and j["choices"]:
                        first = j["choices"][0]
                        if isinstance(first, dict):
                            return {"text": first.get("message", first.get("text", "")) or ""}
                        return {"text": str(first)}
                return {"text": stdout}
            except Exception:
                return {"text": stdout}

        low = (stderr or "").lower()
        if "unknown command" in low or "unrecognized command" in low or "unknown flag" in low:
            continue
        continue

    raise RuntimeError("ollama CLI: no supported subcommand succeeded. Last output: " + (last_out or "<no output>"))


def write_jsonl_line(outfh, obj):
    outfh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", dest="prompt_file", help="CSV prompts file (id,input,reference,...)")
    ap.add_argument("--manifest", dest="manifest", help="manifest JSON (split_manifest.json) - alternative to --prompt-file")
    ap.add_argument("--mode", choices=["general", "instructed"], default="general")
    ap.add_argument("--model", required=True, help="Model name for Ollama, e.g. gemma:7b")
    ap.add_argument("--out", required=True, help="Output JSONL path")
    ap.add_argument("--host", default=DEFAULT_HOST, help="Ollama HTTP host (default http://localhost:11434)")
    ap.add_argument("--use-cli", action="store_true", help="Use ollama CLI instead of HTTP API")
    ap.add_argument("--timeout", type=int, default=120, help="Per-request timeout (seconds)")
    ap.add_argument("--retries", type=int, default=1, help="Number of attempts per prompt (1 = no retry)")
    args = ap.parse_args()

    rows: List[Dict[str, str]] = []
    if args.manifest:
        rows = read_manifest_as_rows(Path(args.manifest))
    elif args.prompt_file:
        p_prompt = Path(args.prompt_file)
        if not p_prompt.exists():
            raise SystemExit(f"[ERR] prompt file not found: {p_prompt}")
        rows = read_prompts_csv(p_prompt)
    else:
        raise SystemExit("[ERR] must provide --prompt-file or --manifest")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    if not args.use_cli and requests is None:
        raise SystemExit("[ERR] requests not installed. Run: pip install requests or use --use-cli")

    with outp.open("w", encoding="utf-8", newline="") as fout:
        for i, row in enumerate(rows):
            id_ = row.get("id") or f"row_{i+1}"
            prompt_text = build_prompt_text(row, args.mode)

            out_text = ""
            error_msg = ""
            latency_ms = 0
            success = False
            for attempt in range(1, max(1, args.retries) + 1):
                start = time.time()
                try:
                    if args.use_cli:
                        result = call_ollama_cli(prompt_text, args.model, args.timeout)
                    else:
                        result = call_ollama_http(prompt_text, args.model, args.host, args.timeout)

                    if isinstance(result, dict):
                        if "text" in result and isinstance(result["text"], str):
                            out_text = result["text"]
                        elif "choices" in result and isinstance(result["choices"], list) and result["choices"]:
                            first = result["choices"][0]
                            if isinstance(first, dict):
                                out_text = first.get("message", first.get("text", "")) or ""
                            else:
                                out_text = str(first)
                        else:
                            out_text = json.dumps(result, ensure_ascii=False)
                    else:
                        out_text = str(result)

                    latency_ms = int((time.time() - start) * 1000)
                    success = True
                    error_msg = ""
                    break

                except subprocess.TimeoutExpired as te:
                    latency_ms = int((time.time() - start) * 1000)
                    error_msg = f"TimeoutExpired: {str(te)}"
                    out_text = ""
                    print(f"[WARN] id={id_} attempt={attempt} error: {error_msg}", file=sys.stderr)
                    if attempt < args.retries:
                        time.sleep(1.0 * attempt)
                    continue

                except requests.exceptions.Timeout as rte:
                    latency_ms = int((time.time() - start) * 1000)
                    error_msg = f"RequestsTimeout: {str(rte)}"
                    out_text = ""
                    print(f"[WARN] id={id_} attempt={attempt} error: {error_msg}", file=sys.stderr)
                    if attempt < args.retries:
                        time.sleep(1.0 * attempt)
                    continue

                except FileNotFoundError as fnf:
                    latency_ms = int((time.time() - start) * 1000)
                    error_msg = f"FileNotFoundError: {str(fnf)}"
                    out_text = ""
                    print(f"[ERR] id={id_} error: {error_msg}", file=sys.stderr)
                    break

                except Exception as e:
                    latency_ms = int((time.time() - start) * 1000)
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    out_text = ""
                    print(f"[WARN] id={id_} attempt={attempt} error: {error_msg}", file=sys.stderr)
                    if attempt < args.retries:
                        time.sleep(1.0 * attempt)
                    continue

            rec: Dict[str, Any] = {
                "id": id_,
                "mode": args.mode,
                "model": args.model,
                "prompt": prompt_text,
                "output": out_text,
                "latency_ms": latency_ms,
                "lang": row.get("lang"),
                "len_bin": row.get("len_bin"),
                "diff_bin": row.get("diff_bin")
            }
            if error_msg:
                rec["error"] = error_msg

            write_jsonl_line(fout, rec)
            print(f"[{i+1}/{len(rows)}] id={id_} latency={latency_ms}ms")

    print(f"[OK] wrote {outp} (n={len(rows)})")


if __name__ == "__main__":
    main()