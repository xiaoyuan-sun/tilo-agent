from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

ToolCallable = Callable[..., Any]


@dataclass
class Tool:
    name: str
    description: str
    args_schema: Dict[str, Any]
    func: ToolCallable

    def call(self, **kwargs: Any) -> Any:
        return self.func(**kwargs)
