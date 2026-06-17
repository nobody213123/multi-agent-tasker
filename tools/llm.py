from __future__ import annotations
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str: ...


class MockLLMProvider(LLMProvider):
    def __init__(self, response: str = ""):
        self._response = response

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._response


class QwenLLMProvider(LLMProvider):
    def __init__(self, model: str = "qwen-turbo", api_key: str = "", temperature: float = 0.7):
        self._model = model
        self._api_key = api_key
        self._temperature = temperature

    def generate(self, prompt: str, system: str | None = None) -> str:
        try:
            from langchain.schema import HumanMessage, SystemMessage
            from langchain_community.chat_models import ChatTongyi

            llm = ChatTongyi(
                model=self._model,
                api_key=self._api_key,
                temperature=self._temperature,
            )
            messages = []
            if system:
                messages.append(SystemMessage(content=system))
            messages.append(HumanMessage(content=prompt))

            response = llm.invoke(messages)
            content = response.content.strip()

            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return content.strip()
        except Exception:
            return ""
