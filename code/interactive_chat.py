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
    "紐⑤뱶": "mode",
    "?쒕굹由ъ삤": "scenario",
    "?꾨━??: "preset",
    "誘몃━?ㅼ젙": "preset",
    "?⑥텞??: "presets",
    "紐⑸줉": "presets",
    "?꾧꺽": "strict",
    "珥덇린??: "clear",
    "?대━??: "clear",
    "?섍?湲?: "exit",
    "醫낅즺": "exit",
}

BANNER = f"""
[??뷀삎 紐⑤뱶 ?ъ슜踰?
紐낅졊:
  /mode general|instructed         (?먮뒗 /紐⑤뱶)
  /scenario <?대쫫> [param=...]     (?먮뒗 /?쒕굹由ъ삤) ?? /scenario format-json keys=city|temp_unit
  /preset <??                     (?먮뒗 /?꾨━??   ?? /preset fj
  /presets                         (?먮뒗 /?⑥텞??   ?꾨━??紐⑸줉 蹂닿린
  /strict on|off                   (?먮뒗 /?꾧꺽 on)
  /clear                           (?먮뒗 /珥덇린??
  /exit                            (?먮뒗 /醫낅즺)

?꾨━???⑥텞?? {", ".join(f"{k}??v[0]}:{v[1]}" for k,v in PRESETS.items())}

TIP:
- ?꾨━???ㅻ쭔 ?낅젰?대룄 ?곸슜?⑸땲?? ?? fj  ?먮뒗  w10
- ?쇰컲 ?낅젰? 紐⑤뜽??洹몃?濡??꾨떖?섎ŉ, ?꾩옱 ?ㅼ젙???쒕굹由ъ삤濡?利됱떆 '以?섍???瑜??섑뻾?⑸땲??
"""


def reason_ko(reason: str) -> str:
    if reason == "ok":
        return "OK"
    if reason == "json_parse_fail":
        return "JSON ?뚯떛 ?ㅽ뙣"
    if reason.startswith("json_keys_mismatch"):
        return "JSON ??遺덉씪移?
    if reason == "digits_forbidden":
        return "?レ옄 湲덉? ?꾨컲(0-9 諛쒓껄)"
    if reason == "non_bullet_lines_present":
        return "遺덈┸ ?댁쇅??以??ы븿"
    if reason.startswith("words="):
        return "?⑥뼱 ??遺덉씪移?(" + reason + ")"
    if reason == "unknown_scenario":
        return "?????녿뒗 ?쒕굹由ъ삤"
    if reason == "not_json_list":
        return "JSON 諛곗뿴???꾨떂"
    if reason.startswith("list_len="):
        return "諛곗뿴 湲몄씠 遺덉씪移?(" + reason + ")"
    if reason.endswith("_not_string"):
        return "諛곗뿴 ??ぉ??臾몄옄?댁씠 ?꾨떂"
    if reason.endswith("_has_space"):
        return "諛곗뿴 ??ぉ??怨듬갚 ?ы븿"
    if reason.startswith("chars="):
        return "湲????遺덉씪移?(" + reason + ")"

    return reason


def build_prompt(mode: str, text: str, strict: bool) -> str:
    p = (
        get_instructed_prompt(text)
        if mode == "instructed"
        else get_general_prompt(text)
    )
    if strict:
        p += "\n\n[?꾧꺽] 吏?쒕맂 ?뺤떇 ?댁쇅??留?癒몃━留??ㅻ챸/肄붾뱶釉붾줉/諛깊떛) 湲덉?. 寃곌낵留?異쒕젰."
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
                f"\n[{mode}{'|?꾧꺽' if strict else ''}{'|'+scenario if scenario else ''}] ?? "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n?덈뀞!")
            return
        if not user:
            continue

        if user[0] in ("/", "!", ".", "竊?):
            cmd, *rest = user[1:].split(" ", 1)
            cmd = normalize_cmd(cmd.strip().lower())
            rest = rest[0] if rest else ""

            if cmd == "exit":
                return

            elif cmd == "mode":
                v = rest.strip()
                if v in ("general", "instructed"):
                    mode = v
                    print(f"-> 紐⑤뱶 蹂寃? {mode}")
                else:
                    print("?ъ슜踰? /mode general|instructed")

            elif cmd == "scenario":
                parts = rest.split(" ", 1)
                scenario = parts[0].strip() if parts and parts[0] else None
                params = parse_params(parts[1] if len(parts) > 1 else "")
                print(f"-> ?쒕굹由ъ삤={scenario}, ?뚮씪誘명꽣={params}")

            elif cmd == "preset":
                scen, pr, ok = apply_preset(rest)
                if ok:
                    scenario, params = scen, pr
                    print(f"-> ?꾨━??'{rest}' ?곸슜: {scenario} {params}")
                else:
                    print("?????녿뒗 ?꾨━???? /presets 濡?紐⑸줉 ?뺤씤")

            elif cmd == "presets":
                print("?꾨━??紐⑸줉:")
                for k, (sc, pr) in PRESETS.items():
                    print(f"  {k:>4} -> {sc} {pr}")

            elif cmd == "strict":
                strict = rest.strip().lower() == "on"
                print(f"-> ?꾧꺽 紐⑤뱶: {strict}")

            elif cmd == "clear":
                scenario, params, strict = None, {}, False
                print("-> ?곹깭 珥덇린???꾨즺")

            elif cmd in PRESETS:
                scen, pr, _ = apply_preset(cmd)
                scenario, params = scen, pr
                print(f"-> ?꾨━??'{cmd}' ?곸슜: {scenario} {params}")
            else:
                print("?????녿뒗 紐낅졊. /presets 濡??꾩?留??뺤씤")
            continue

        scen, pr, ok = apply_preset(user)
        if ok:
            scenario, params = scen, pr
            print(f"-> ?꾨━??'{user}' ?곸슜: {scenario} {params}")
            continue

        prompt = build_prompt(mode, user, strict)
        out = llm.generate(prompt)
        print(f"AI> {out}")

        if scenario:
            ok, reason = evaluate_item(scenario, out, params)
            mark = "?? if ok else "??
            print(f"[以?섍??? {mark} {reason_ko(reason)}")

            if not ok and scenario == "limit-words":
                n = params.get("words", "")
                retry_hint = (
                    f"\n\n[?ъ옉?? ??異쒕젰? {n}?⑥뼱媛 ?꾨떃?덈떎. "
                    f"?꾨옒 洹쒖튃??紐⑤몢 吏耳?'理쒖쥌 寃곌낵留? ?ㅼ떆 ?곗꽭??\n"
                    f"- ?뺥솗??{n}?⑥뼱\n"
                    f"- 媛??⑥뼱??怨듬갚 ??移몄쑝濡쒕쭔 援щ텇\n"
                    f"- 臾몄옣遺?맞룹닽??湲덉?\n"
                    f"- 異쒕젰?뺤떇: ?⑥뼱1 ?⑥뼱2 ???⑥뼱{n}\n"
                )
                retry_prompt = build_prompt(mode, user + retry_hint, strict=True)
                retry_out = llm.generate(retry_prompt)
                print(f"AI(?ъ떆??> {retry_out}")
                ok2, reason2 = evaluate_item(scenario, retry_out, params)
                mark2 = "?? if ok2 else "??
                print(f"[以?섍????ъ떆?? {mark2} {reason_ko(reason2)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["general", "instructed"], default="instructed")
    ap.add_argument("--provider", choices=["openai", "ollama"], default="ollama")
    ap.add_argument("--model", default="gemma:7b-instruct")
    ap.add_argument("--temperature", type=float, default=0.2)
    a = ap.parse_args()
    main(a)
