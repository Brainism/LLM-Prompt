from typing import Optional

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None  # type: ignore

try:
    from langchain_ollama import ChatOllama
except Exception:
    ChatOllama = None  # type: ignore

from langchain_core.messages import HumanMessage, SystemMessage


class LLMWrapper:
    def __init__(
        self,
        provider: str,
        model: str,
        temperature: float = 0.2,
        num_predict: Optional[int] = None,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.num_predict = num_predict

    def _chat(self):
        if self.provider == "openai":
            if ChatOpenAI is None:
                raise RuntimeError("langchain-openai ?꾪룷???ㅽ뙣 ?먮뒗 誘몄꽕移?)
            return ChatOpenAI(model=self.model, temperature=self.temperature)
        elif self.provider == "ollama":
            if ChatOllama is None:
                raise RuntimeError("langchain-ollama ?꾪룷???ㅽ뙣 ?먮뒗 誘몄꽕移?)
            kwargs = {"model": self.model, "temperature": self.temperature}
            if self.num_predict is not None:
                kwargs["num_predict"] = self.num_predict
            return ChatOllama(**kwargs)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def generate(self, prompt: str) -> str:
        chat = self._chat()
        msgs = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt),
        ]
        resp = chat.invoke(msgs)
        return getattr(resp, "content", str(resp))


def get_llm(
    provider: str,
    model: str,
    temperature: float = 0.2,
    num_predict: Optional[int] = None,
) -> LLMWrapper:
    return LLMWrapper(
        provider=provider, model=model, temperature=temperature, num_predict=num_predict
    )
