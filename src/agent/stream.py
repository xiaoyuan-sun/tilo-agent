# src/agent/stream.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class StreamEvent:
    """流式输出事件"""
    type: Literal["thinking", "tool_call", "text", "done"]
    data: str
