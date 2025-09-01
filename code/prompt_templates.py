from __future__ import annotations


def _needs_title_tags_json(text: str) -> bool:
    """
    ?낅젰 吏?쒕Ц??'title, tags' JSON???붽뎄?섎뒗吏 媛꾨떒???먯젙.
    - ?곷Ц/援?Ц 耳?댁뒪 紐⑤몢 'json' 臾몄옄???ы븿 媛??
    - title/tags ??紐낆떆 ?щ? ?뺤씤
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
    return "?붿껌???듯븯?쒖삤. ?꾩슂?섎떎硫?媛꾨떒???ㅻ챸?대룄 ?⑸땲??\n\n" f"{text}"


def get_instructed_prompt(text: str) -> str:
    """
    - ?꾩뿭 洹쒖튃??癒쇱? ?쒖떆
    - ?낅젰??'title/tags JSON'???붽뎄?섎㈃ JSON ?꾩슜 ?뺤콉 釉붾줉??異붽?
    - 留덉?留됱뿉 吏?쒕Ц ?먮Ц??洹몃?濡?泥⑤?
    """
    parts = [
        "??븷: ?뱀떊? 吏?쒕? '?꾧꺽?? ?곕Ⅴ???쒓뎅??鍮꾩꽌?낅땲??",
        "?꾩뿭 洹쒖튃:",
        "- 吏?쒕맂 ?뺤떇 ?댁쇅??留?癒몃━留??ㅻ챸/肄붾뱶釉붾줉/諛깊떛/異붽? 臾몄옣) ?덈? 湲덉?",
        "- 'JSON' 吏?쒓? ?덉쑝硫?JSON 媛앹껜留?異쒕젰(???뺥솗, ?곗샂?쒕뒗 ?띾뵲?댄몴)",
        "- '?뺥솗??N?⑥뼱' 吏?쒕뒗 怨듬갚 湲곗? N?⑥뼱留?異쒕젰(留덉묠????遺덊븘?뷀븳 湲고샇 湲덉?)",
        "- '遺덈┸ n媛? 吏?쒕뒗 '-'濡??쒖옉?섎뒗 n以꾨쭔 異쒕젰(鍮덉쨪 湲덉?)",
        "- '?レ옄 湲덉?' 吏?쒕뒗 0-9瑜??덈? 異쒕젰?섏? ?딆쓬",
        "",
        "?덉떆1 (JSON留?:",
        "?붿껌: ?뺥솗???ㅼ쓬 ?ㅻ쭔 ?ы븿??JSON?쇰줈留?異쒕젰?섎씪: city(?쒖슱), temp_unit(C). 異붽? ?띿뒪??湲덉?.",
        '異쒕젰: {"city":"?쒖슱","temp_unit":"C"}',
        "",
        "?덉떆2 (遺덈┸):",
        "?붿껌: ?쇰㈃ ?볦씠???덉감瑜?2媛쒖쓽 遺덈┸?쇰줈留??⑤씪. 媛?以꾩? '-'濡??쒖옉. ?ㅻⅨ 留?湲덉?.",
        "異쒕젰:",
        "- 臾??볦씠湲?,
        "- 硫??ｊ린",
        "",
        "?덉떆3 (?⑥뼱??:",
        "?붿껌: ?ㅼ쓬 臾몄옣???뺥솗??3?⑥뼱濡??붿빟?섎씪: ?멸났吏?μ? 留ㅼ슦 ?좎슜?섎떎",
        "異쒕젰: ?멸났吏?μ? 留ㅼ슦?좎슜?섎떎 ?붿빟",
        "",
        "?덉떆4 (?レ옄 湲덉?):",
        "?붿껌: ?꾨옒 ?섎웾???쒓?濡쒕쭔 ?곸뼱?? 3媛?4媛?,
        "異쒕젰: ??媛???媛?,
        "",
    ]

    if _needs_title_tags_json(text):
        parts.extend(
            [
                "[STRICT JSON OUTPUT POLICY]",
                JSON_ONLY_TITLE_TAGS_POLICY,
                "",
            ]
        )

    parts.extend(
        [
            "吏?쒕Ц(洹몃?濡??곕Ⅴ?쒖삤):",
            f"{text}",
        ]
    )

    return "\n".join(parts)
