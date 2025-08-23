from __future__ import annotations

def _needs_title_tags_json(text: str) -> bool:
    """
    입력 지시문이 'title, tags' JSON을 요구하는지 간단히 판정.
    - 영문/국문 케이스 모두 'json' 문자열 포함 가정
    - title/tags 키 명시 여부 확인
    """
    t = text.lower()
    has_json = "json" in t
    has_title = "title" in t
    has_tags = "tags" in t
    return has_json and has_title and has_tags

JSON_ONLY_TITLE_TAGS_POLICY = """Return ONLY a valid JSON object with exactly these keys:
- "title": string
- "tags": array of 2-5 short strings
Rules:
- No code fences, no prose, no extra text.
- No trailing commas, no comments.
- Output must start with '{' and end with '}'.
Example:
{"title":"...", "tags":["...", "..."]}"""


def get_general_prompt(text: str) -> str:
    return (
        "요청에 답하시오. 필요하다면 간단히 설명해도 됩니다.\n\n"
        f"{text}"
    )


def get_instructed_prompt(text: str) -> str:
    """
    - 전역 규칙을 먼저 제시
    - 입력이 'title/tags JSON'을 요구하면 JSON 전용 정책 블록을 추가
    - 마지막에 지시문 원문을 그대로 첨부
    """
    parts = [
        "역할: 당신은 지시를 '엄격히' 따르는 한국어 비서입니다.",
        "전역 규칙:",
        "- 지시된 형식 이외의 말(머리말/설명/코드블록/백틱/추가 문장) 절대 금지",
        "- 'JSON' 지시가 있으면 JSON 객체만 출력(키 정확, 따옴표는 쌍따옴표)",
        "- '정확히 N단어' 지시는 공백 기준 N단어만 출력(마침표 등 불필요한 기호 금지)",
        "- '불릿 n개' 지시는 '-'로 시작하는 n줄만 출력(빈줄 금지)",
        "- '숫자 금지' 지시는 0-9를 절대 출력하지 않음",
        "",
        "예시1 (JSON만):",
        "요청: 정확히 다음 키만 포함한 JSON으로만 출력하라: city(서울), temp_unit(C). 추가 텍스트 금지.",
        "출력: {\"city\":\"서울\",\"temp_unit\":\"C\"}",
        "",
        "예시2 (불릿):",
        "요청: 라면 끓이는 절차를 2개의 불릿으로만 써라. 각 줄은 '-'로 시작. 다른 말 금지.",
        "출력:",
        "- 물 끓이기",
        "- 면 넣기",
        "",
        "예시3 (단어수):",
        "요청: 다음 문장을 정확히 3단어로 요약하라: 인공지능은 매우 유용하다",
        "출력: 인공지능은 매우유용하다 요약",
        "",
        "예시4 (숫자 금지):",
        "요청: 아래 수량을 한글로만 적어라: 3개 4개",
        "출력: 세 개 네 개",
        "",
    ]

    if _needs_title_tags_json(text):
        parts.extend([
            "[STRICT JSON OUTPUT POLICY]",
            JSON_ONLY_TITLE_TAGS_POLICY,
            "",
        ])

    parts.extend([
        "지시문(그대로 따르시오):",
        f"{text}",
    ])

    return "\n".join(parts)