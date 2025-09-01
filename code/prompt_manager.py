from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class PromptItem:
    id: str
    prompt_type: str
    text: str


def load_prompts(
    csv_path: str, text_col: str = "text", id_col: str | None = "prompt_id"
) -> list[PromptItem]:
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(p)
    try:
        df = pd.read_csv(p, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(p, encoding="utf-8-sig")

    items: list[PromptItem] = []
    for i, row in df.iterrows():
        pid = str(row[id_col]) if id_col and id_col in df.columns else str(i + 1)
        ptype = str(row.get("prompt_type", "general"))
        txt = str(row[text_col])
        items.append(PromptItem(id=pid, prompt_type=ptype, text=txt))
    return items
