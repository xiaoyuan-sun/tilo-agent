from __future__ import annotations

import os
import re
from typing import Any, Mapping, Protocol, Sequence, TypeAlias
from uuid import uuid4

from agentscope.model import OpenAIChatModel
from dotenv import load_dotenv

try:
    from agentscope.message import ToolUseBlock, TextBlock
except (ImportError, ModuleNotFoundError):
    ToolUseBlock: TypeAlias = dict[str, Any]
    TextBlock: TypeAlias = dict[str, Any]


PromptBlock = Mapping[str, Any]


class ModelResponse:
    def __init__(self, content: Sequence[Mapping[str, Any]], metadata: Mapping[str, Any] | None = None) -> None:
        self.content = list(content)
        self.metadata = metadata or {}


class BaseModel(Protocol):
    stream: bool

    async def __call__(self, prompt: Sequence[PromptBlock], **kwargs: Any) -> ModelResponse:
        ...


class MockModel:
    stream = False

    async def __call__(self, prompt: Sequence[PromptBlock], **kwargs: Any) -> ModelResponse:
        user_text = self._extract_latest_user_text(prompt)
        if self._detect_time_intent(user_text):
            return ModelResponse([self._build_tool_use("time.now", {})])
        expression = self._extract_math_expression(user_text)
        if expression:
            return ModelResponse([self._build_tool_use("math.calc", {"expression": expression})])
        return ModelResponse([self._build_text_block("这是一个模拟回答，未检测到需要工具的意图。")])

    def _extract_latest_user_text(self, prompt: Sequence[PromptBlock]) -> str:
        for message in reversed(prompt):
            if message.get("role") != "user":
                continue
            content = message.get("content", [])
            texts = [block.get("text") for block in content if isinstance(block, dict) and block.get("text")]
            if texts:
                return "\n".join(texts)
        return ""

    def _detect_time_intent(self, text: str) -> bool:
        lowered = text.lower()
        keywords = ["time", "几点", "时间", "date", "today", "now", "current"]
        return any(keyword in lowered for keyword in keywords)

    def _extract_math_expression(self, text: str) -> str | None:
        candidate = re.search(r"([0-9. ()+-/*]+[+\-*/][0-9. ()+-/*]+)", text)
        if not candidate:
            return None
        expression = candidate.group(1).strip()
        if expression:
            return expression
        return None

    def _build_tool_use(self, name: str, args: Mapping[str, Any]) -> ToolUseBlock:
        return {
            "type": "tool_use",
            "id": uuid4().hex,
            "name": name,
            "input": args,
        }

    def _build_text_block(self, text: str) -> TextBlock:
        return {"type": "text", "text": text}


def build_model_from_env() -> BaseModel:
    load_dotenv(override=False)
    provider = os.environ.get("AGENTSCOPE_MODEL", "").strip().lower()
    if not provider:
        return MockModel()
    model_name = os.environ.get("AGENTSCOPE_MODEL_NAME", "").strip()
    if not model_name:
        raise ValueError("AGENTSCOPE_MODEL_NAME is required when AGENTSCOPE_MODEL is set.")
    if provider == "openai":
        api_key = os.environ.get("AGENTSCOPE_API_KEY")
        base_url = os.environ.get("AGENTSCOPE_BASE_URL", "").strip()
        client_kwargs = {"base_url": base_url} if base_url else None
        return OpenAIChatModel(
            model_name=model_name,
            api_key=api_key,
            stream=False,
            client_kwargs=client_kwargs,
        )
    raise ValueError(f"Unsupported AGENTSCOPE_MODEL provider: {provider}")
