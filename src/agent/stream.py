# src/agent/stream.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class StreamEvent:
    """流式输出事件"""
    type: Literal["thinking", "tool_call", "text", "done"]
    data: str


class StreamingHook:
    """通过 hooks 收集事件，供 chat_stream 使用"""

    def __init__(self, queue: asyncio.Queue[StreamEvent | None]) -> None:
        self.queue = queue

    def pre_reasoning(self, agent: Any, kwargs: dict[str, Any]) -> None:
        """推理开始前，emit thinking 事件"""
        self.queue.put_nowait(StreamEvent("thinking", ""))

    def pre_acting(self, agent: Any, kwargs: dict[str, Any]) -> None:
        """工具执行前，emit tool_call 事件"""
        tool_name = kwargs.get("parsed", {}).get("name", "unknown")
        self.queue.put_nowait(StreamEvent("tool_call", str(tool_name)))
