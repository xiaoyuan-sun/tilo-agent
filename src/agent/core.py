from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Mapping

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.tool import ToolResponse, Toolkit, view_text_file, write_text_file

from agent.prompt_builder import build_sys_prompt
from agent.prompt_files import compose_prompt_context
from llm.client import build_model_from_env
from memory.jsonl_store import JsonlMemoryStore
from mcp_support.registry import auto_register_mcp_clients
from runtime.session import SessionContext
from skills.loader import load_enabled_skills


def _tool_signature_text(fn: Callable[..., Any]) -> str:
    return f"{fn.__name__}{inspect.signature(fn)}"


def _enable_builtin_file_tools(toolkit: Toolkit, _project_root: Any) -> list[str]:
    toolkit.register_tool_function(view_text_file)
    toolkit.register_tool_function(write_text_file)
    return [_tool_signature_text(view_text_file), _tool_signature_text(write_text_file)]


async def _append_memory_entry(memory: object, entry: Any) -> None:
    if hasattr(memory, "append"):
        result = getattr(memory, "append")(entry)
        if inspect.isawaitable(result):
            await result
        return
    if hasattr(memory, "add"):
        result = getattr(memory, "add")(entry)
        if inspect.isawaitable(result):
            await result
        return
    raise AttributeError("Memory object must provide append() or add().")


def _history_entry_to_msg(entry: Msg | Mapping[str, Any]) -> Msg:
    if isinstance(entry, Msg):
        return entry
    role = str(entry.get("role") or "assistant")
    name = str(entry.get("name") or role)
    content = entry.get("content", "")
    return Msg(name=name, role=role, content=content)


def _normalize_response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, Mapping):
        text = content.get("text")
        return str(text) if text is not None else json.dumps(content, ensure_ascii=False)
    if isinstance(content, list):
        texts = [
            str(block.get("text"))
            for block in content
            if isinstance(block, Mapping) and block.get("text") is not None
        ]
        if texts:
            return "\n".join(texts)
        return json.dumps(content, ensure_ascii=False)
    if content is None:
        return ""
    return str(content)


async def run_once(user_text: str, ctx: SessionContext) -> str:
    _, skill_dirs = load_enabled_skills(ctx.enabled_skills)
    toolkit = Toolkit()
    tool_lines = _enable_builtin_file_tools(toolkit, ctx.project_root)
    mcp_manager = await auto_register_mcp_clients(toolkit)
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    tool_lines.append("(plus tool functions provided by registered AgentScope skills)")
    if mcp_manager.client_names:
        tool_lines.append(
            f"(plus MCP tool functions provided by: {', '.join(mcp_manager.client_names)})"
        )
    prompt_context = compose_prompt_context(ctx.workspace_dir())
    sys_prompt = build_sys_prompt(prompt_context, "\n".join(tool_lines))
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id, user_id=ctx.user_id)
    memory = InMemoryMemory()
    for entry in history:
        await _append_memory_entry(memory, _history_entry_to_msg(entry))
    model = build_model_from_env()
    agent = ReActAgent(
        name="Tilo",
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=memory,
        max_iters=ctx.max_iters,
    )
    user_msg = Msg(name="user", content=user_text, role="user")
    try:
        response = await agent(user_msg)
        assistant_text = _normalize_response_text(response.content)
        memory_store.append(
            ctx.session_id, {"role": "user", "content": user_text}, user_id=ctx.user_id
        )
        memory_store.append(
            ctx.session_id,
            {"role": "assistant", "content": assistant_text},
            user_id=ctx.user_id,
        )
        return assistant_text
    finally:
        await mcp_manager.close()
