from __future__ import annotations

import argparse

from compliance_rules import evaluate_item, parse_params
from llm_factory import get_llm
from prompt_templates import get_general_prompt, get_instructed_prompt

PRESETS = {
    "fj": ("format-json", {"keys": "city|temp_unit"}),
    "fj2": ("format-json", {"keys": "product|price"}),
    "w10": ("limit-words", {"words": "10"}),
    "w12": ("limit-words", {"words": "12"}),
    "b4": ("bullets", {"bullets": "4"}),
    "b5": ("bullets", {"bullets": "5"}),
    "fd": ("forbid-terms", {"forbid": "digits"}),
    "w10j": ("limit-items-json", {"n": "10", "no_space": "true"}),
    "w12j": ("limit-items-json", {"n": "12", "no_space": "true"}),
    "c20": ("limit-chars", {"chars": "20", "mode": "nonspace"}),
}

ALIASES = {
    "모드": "mode",
    "시나리오": "scenario",
    "프리셋": "preset",
    "미리설정": "preset",
    "단축키": "presets",
    "목록": "presets",
    "엄격": "strict",
    "초기화": "clear",
    "클리어": "clear",
    "나가기": "exit",
    "종료": "exit",
}

BANNER = f"""
[대화형 모드 사용법]
명령:
  /mode general|instructed         (또는 /모드)
  /scenario <이름> [param=...]     (또는 /시나리오) 예: /scenario format-json keys=city|temp_unit
  /preset <키>                     (또는 /프리셋)   예: /preset fj
  /presets                         (또는 /단축키)   프리셋 목록 보기
  /strict on|off                   (또는 /엄격 on)
  /clear                           (또는 /초기화)
  /exit                            (또는 /종료)

프리셋 단축키: {", ".join(f"{k}→{v[0]}:{v[1]}" for k,v in PRESETS.items())}

TIP:
- 프리셋 키만 입력해도 적용됩니다. 예) fj  또는  w10
- 일반 입력은 모델에 그대로 전달되며, 현재 설정된 시나리오로 즉시 '준수검사'를 수행합니다.
"""


def reason_ko(reason: str) -> str:
    if reason == "ok":
        return "OK"
    if reason == "json_parse_fail":
        return "JSON 파싱 실패"
    if reason.startswith("json_keys_mismatch"):
        return "JSON 키 불일치"
    if reason == "digits_forbidden":
        return "숫자 금지 위반(0-9 발견)"
    if reason == "non_bullet_lines_present":
        return "불릿 이외의 줄 포함"
    if reason.startswith("words="):
        return "단어 수 불일치 (" + reason + ")"
    if reason == "unknown_scenario":
        return "알 수 없는 시나리오"
    if reason == "not_json_list":
        return "JSON 배열이 아님"
    if reason.startswith("list_len="):
        return "배열 길이 불일치 (" + reason + ")"
    if reason.endswith("_not_string"):
        return "배열 항목에 문자열이 아님"
    if reason.endswith("_has_space"):
        return "배열 항목에 공백 포함"
    if reason.startswith("chars="):
        return "글자 수 불일치 (" + reason + ")"

    return reason


def build_prompt(mode: str, text: str, strict: bool) -> str:
    p = (
        get_instructed_prompt(text)
        if mode == "instructed"
        else get_general_prompt(text)
    )
    if strict:
        p += "\n\n[엄격] 지시된 형식 이외의 말(머리말/설명/코드블록/백틱) 금지. 결과만 출력."
    return p


def apply_preset(key: str):
    k = key.strip().lower()
    if k in PRESETS:
        scen, params = PRESETS[k]
        return scen, params, True
    return None, None, False


def normalize_cmd(cmd: str) -> str:
    return ALIASES.get(cmd, cmd)


def main(args):
    llm = get_llm(args.provider, args.model, temperature=args.temperature)
    mode = args.mode
    strict = False
    scenario: str | None = None
    params: dict[str, str] = {}

    print(BANNER.strip())
    while True:
        try:
            user = input(
                f"\n[{mode}{'|엄격' if strict else ''}{'|'+scenario if scenario else ''}] 나> "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n안녕!")
            return
        if not user:
            continue

        if user[0] in ("/", "!", ".", "／"):
            cmd, *rest = user[1:].split(" ", 1)
            cmd = normalize_cmd(cmd.strip().lower())
            rest = rest[0] if rest else ""

            if cmd == "exit":
                return

            elif cmd == "mode":
                v = rest.strip()
                if v in ("general", "instructed"):
                    mode = v
                    print(f"-> 모드 변경: {mode}")
                else:
                    print("사용법: /mode general|instructed")

            elif cmd == "scenario":
                parts = rest.split(" ", 1)
                scenario = parts[0].strip() if parts and parts[0] else None
                params = parse_params(parts[1] if len(parts) > 1 else "")
                print(f"-> 시나리오={scenario}, 파라미터={params}")

            elif cmd == "preset":
                scen, pr, ok = apply_preset(rest)
                if ok:
                    scenario, params = scen, pr
                    print(f"-> 프리셋 '{rest}' 적용: {scenario} {params}")
                else:
                    print("알 수 없는 프리셋 키. /presets 로 목록 확인")

            elif cmd == "presets":
                print("프리셋 목록:")
                for k, (sc, pr) in PRESETS.items():
                    print(f"  {k:>4} -> {sc} {pr}")

            elif cmd == "strict":
                strict = rest.strip().lower() == "on"
                print(f"-> 엄격 모드: {strict}")

            elif cmd == "clear":
                scenario, params, strict = None, {}, False
                print("-> 상태 초기화 완료")

            elif cmd in PRESETS:
                scen, pr, _ = apply_preset(cmd)
                scenario, params = scen, pr
                print(f"-> 프리셋 '{cmd}' 적용: {scenario} {params}")
            else:
                print("알 수 없는 명령. /presets 로 도움말 확인")
            continue

        scen, pr, ok = apply_preset(user)
        if ok:
            scenario, params = scen, pr
            print(f"-> 프리셋 '{user}' 적용: {scenario} {params}")
            continue

        prompt = build_prompt(mode, user, strict)
        out = llm.generate(prompt)
        print(f"AI> {out}")

        if scenario:
            ok, reason = evaluate_item(scenario, out, params)
            mark = "✓" if ok else "✗"
            print(f"[준수검사] {mark} {reason_ko(reason)}")

            if not ok and scenario == "limit-words":
                n = params.get("words", "")
                retry_hint = (
                    f"\n\n[재작성] 위 출력은 {n}단어가 아닙니다. "
                    f"아래 규칙을 모두 지켜 '최종 결과만' 다시 쓰세요.\n"
                    f"- 정확히 {n}단어\n"
                    f"- 각 단어는 공백 한 칸으로만 구분\n"
                    f"- 문장부호·숫자 금지\n"
                    f"- 출력형식: 단어1 단어2 … 단어{n}\n"
                )
                retry_prompt = build_prompt(mode, user + retry_hint, strict=True)
                retry_out = llm.generate(retry_prompt)
                print(f"AI(재시도)> {retry_out}")
                ok2, reason2 = evaluate_item(scenario, retry_out, params)
                mark2 = "✓" if ok2 else "✗"
                print(f"[준수검사-재시도] {mark2} {reason_ko(reason2)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["general", "instructed"], default="instructed")
    ap.add_argument("--provider", choices=["openai", "ollama"], default="ollama")
    ap.add_argument("--model", default="gemma:7b-instruct")
    ap.add_argument("--temperature", type=float, default=0.2)
    a = ap.parse_args()
    main(a)
