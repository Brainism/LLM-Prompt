from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def parse_params(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        return {}
    if raw.startswith("{") and raw.endswith("}"):
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    out: Dict[str, Any] = {}
    for tok in shlex.split(raw):
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k.strip()] = _coerce_scalar(v.strip())
        else:
            out[tok.strip()] = True
    return out


def _coerce_scalar(s: str) -> Any:
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lower() in ("none", "null"):
        return None
    try:
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        return s


def extract_json_from_text(text: str) -> Optional[Any]:
    if not text:
        return None
    patterns = [r"\{.*\}", r"\[.*\]"]
    for pat in patterns:
        m = re.search(pat, text, flags=re.DOTALL)
        if m:
            sub = m.group(0)
            try:
                return json.loads(sub)
            except Exception:
                continue
    return None


@dataclass
class EvalResult:
    ok: bool
    reason: str = ""


def evaluate_item(
    scenario: Optional[str], output_text: str, params: Dict[str, Any]
) -> EvalResult:
    scn = (scenario or "").strip().lower() or "none"

    if scn == "json_array_len":
        obj = extract_json_from_text(output_text)
        if not isinstance(obj, dict):
            return EvalResult(False, "no_json_object_found")
        json_key = str(params.get("json_key", "items"))
        arr = obj.get(json_key)
        if not isinstance(arr, list):
            return EvalResult(False, f"json_key_not_list:{json_key}")
        min_items = int(params.get("min", 1))
        max_items = int(params.get("max", 5))
        n = len(arr)
        if n < min_items or n > max_items:
            return EvalResult(
                False, f"len_out_of_range:{n} not in [{min_items},{max_items}]"
            )
        return EvalResult(True, "ok")

    if scn == "json_keys":
        obj = extract_json_from_text(output_text)
        if not isinstance(obj, dict):
            return EvalResult(False, "no_json_object_found")
        req = params.get("required_keys") or params.get("keys") or []
        if not isinstance(req, (list, tuple)):
            return EvalResult(False, "required_keys_not_list")
        missing = [k for k in req if k not in obj]
        if missing:
            return EvalResult(False, f"missing_keys:{','.join(map(str, missing))}")
        return EvalResult(True, "ok")

    if scn == "digits_forbidden":
        if re.search(r"[0-9]", output_text):
            return EvalResult(False, "digits_present")
        return EvalResult(True, "ok")

    return EvalResult(True, "no_scenario")


def reason_ko(reason: str) -> str:
    mapping = {
        "ok": "정상",
        "no_json_object_found": "출력에서 JSON 객체를 찾지 못했습니다.",
        "required_keys_not_list": "required_keys 파라미터가 리스트가 아닙니다.",
        "digits_present": "출력에 숫자가 포함되어 있습니다.",
    }
    if reason.startswith("json_key_not_list:"):
        return f"지정 키가 리스트가 아닙니다 ({reason.split(':',1)[1]})."
    if reason.startswith("len_out_of_range:"):
        return f"배열 길이가 허용 범위를 벗어났습니다 ({reason.split(':',1)[1]})."
    if reason.startswith("missing_keys:"):
        return f"필수 키 누락: {reason.split(':',1)[1]}"
    return mapping.get(reason, reason)


PRESETS: Dict[str, Tuple[str, Dict[str, Any]]] = {
    "g": ("none", {}),
    "i": ("digits_forbidden", {}),
    "len3": ("json_array_len", {"json_key": "tags", "min": 3, "max": 3}),
    "keys_basic": ("json_keys", {"required_keys": ["id", "name"]}),
}


def apply_preset(name: str) -> Tuple[Optional[str], Dict[str, Any], bool]:
    key = (name or "").strip().lower()
    if key in PRESETS:
        scn, params = PRESETS[key]
        return scn, dict(params), True
    return None, {}, False


def normalize_cmd(s: str) -> str:
    return (s or "").lower().strip()


def print_help() -> None:
    print(
        """Commands:
  /help
  /exit
  /clear
  /mode general|instructed
  /scenario <name> [k=v ... | {"json":"ok"}]
  /preset <name>
  /presets
  /strict on|off

Examples:
  /mode general
  /scenario json_array_len json_key=items min=2 max=5
  /scenario json_keys {"required_keys":["id","name"]}
  /preset len3
  /strict on
  (아무것도 안 붙이고) 모델 출력 붙여넣기 → 현재 시나리오로 검증
"""
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Strict 모드로 시작")
    args = ap.parse_args()

    mode = "general"
    scenario: Optional[str] = None
    params: Dict[str, Any] = {}
    strict = bool(args.strict)

    print("=== Interactive Eval ===")
    print("'/help' 로 명령 안내를 보세요. '/exit' 로 종료.")
    print(f"현재 모드: {mode}, strict={strict}")

    while True:
        try:
            user = input("> ").rstrip("\n")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return

        if not user:
            continue

        if user[0] in ("/", "!", "."):
            cmdline = user[1:].strip()
            if not cmdline:
                continue
            cmd, *rest = cmdline.split(" ", 1)
            arg = rest[0] if rest else ""
            cmd = normalize_cmd(cmd)

            if cmd in ("exit", "quit"):
                return
            if cmd in ("h", "help"):
                print_help()
                continue
            if cmd == "clear":
                mode, scenario, params, strict = "general", None, {}, False
                print("상태 초기화 완료.")
                continue
            if cmd == "mode":
                v = normalize_cmd(arg)
                if v in ("general", "instructed"):
                    mode = v
                    print(f"-> mode={mode}")
                else:
                    print("사용법: /mode general|instructed")
                continue
            if cmd == "scenario":
                name, pstr = (arg.split(" ", 1) + [""])[:2] if arg else ("", "")
                if not name:
                    print("사용법: /scenario <name> [k=v ... | {json}]")
                    continue
                scenario = name.strip()
                params = parse_params(pstr)
                print(f"-> scenario={scenario} params={params}")
                continue
            if cmd == "preset":
                scn, pr, ok = apply_preset(arg)
                if ok:
                    scenario, params = scn, pr
                    print(f"-> preset 적용: {arg} -> {scenario} {params}")
                else:
                    print("알 수 없는 프리셋. /presets 로 목록 확인")
                continue
            if cmd == "presets":
                print("프리셋 목록:")
                for k, (scn, pr) in PRESETS.items():
                    print(f"  {k:>8} -> {scn} {pr}")
                continue
            if cmd == "strict":
                v = normalize_cmd(arg)
                strict = v == "on"
                print(f"-> strict={strict}")
                continue

            print("알 수 없는 명령. /help 참고.")
            continue

        output_text = user

        if strict and len(output_text.strip()) < 3:
            print("[검증] 너무 짧은 응답입니다 (strict).")
            continue

        res = evaluate_item(scenario, output_text, params)
        mark = "✅" if res.ok else "❌"
        print(f"[결과] {mark} {reason_ko(res.reason)}")


if __name__ == "__main__":
    main()
