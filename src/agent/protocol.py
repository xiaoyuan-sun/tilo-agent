from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

ToolPayload = Dict[str, Any]


@dataclass(frozen=True)
class ToolAction:
    name: str
    args: ToolPayload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolAction":
        return cls(name=str(data.get("name", "")), args=data.get("args", {}))


@dataclass(frozen=True)
class FinalAction:
    result: str

    @classmethod
    def from_result(cls, value: str) -> "FinalAction":
        return cls(result=value)
