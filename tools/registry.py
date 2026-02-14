from __future__ import annotations

from typing import List

from agentscope.tool import Toolkit

from tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: List[Tool] = []

    def register(self, tool: Tool) -> None:
        self._tools.append(tool)

    def list_for_prompt(self) -> str:
        if not self._tools:
            return "(no registered tools)"
        return "\n".join(
            f"{tool.name}: {tool.description} | args={tool.args_schema}" for tool in self._tools
        )

    def to_agentscope_toolkit(self):
        tk = Toolkit()
        for tool in self._tools:
            self._register_tool(tk, tool)
        return tk

    def _register_tool(self, tk, tool: Tool) -> None:
        register = getattr(tk, "register_tool_function")
        try:
            register(
                tool.func,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
            )
        except TypeError:
            try:
                register(tool.func, tool.name, description=tool.description)
            except TypeError:
                register(tool.func, tool.name)

    def call(self, name: str, **kwargs) -> any:
        for tool in self._tools:
            if tool.name == name:
                return tool.func(**kwargs)
        raise KeyError(f"Tool '{name}' is not registered")
