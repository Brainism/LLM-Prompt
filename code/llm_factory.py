from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None

try:
    from langchain_community.chat_models import ChatOllama
except Exception:
    ChatOllama = None


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    num_predict: Optional[int] = None


class LLMFactory:
    def __init__(self, cfg: LLMConfig):
        self.provider = cfg.provider.lower()
        self.model = cfg.model
        self.temperature = cfg.temperature
        self.num_predict = cfg.num_predict

    def build(self):
        if self.provider == "openai":
            if ChatOpenAI is None:
                raise RuntimeError(
                    "langchain-openai가 설치되어 있지 않습니다. pip install langchain-openai"
                )
            return ChatOpenAI(model=self.model, temperature=self.temperature)

        elif self.provider == "ollama":
            if ChatOllama is None:
                raise RuntimeError(
                    "langchain-community가 설치되어 있지 않습니다. pip install langchain-community"
                )
            kwargs = {"model": self.model, "temperature": self.temperature}
            if self.num_predict is not None:
                kwargs["num_predict"] = self.num_predict
            return ChatOllama(**kwargs)

        else:
            raise ValueError(f"Unknown provider: {self.provider}")