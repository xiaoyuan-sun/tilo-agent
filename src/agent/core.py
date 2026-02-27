from __future__ import annotations

from functools import wraps
import inspect
import json
from pathlib import Path
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
from runtime.file_access import ensure_writable, resolve_project_path
from runtime.session import SessionContext
from skills.loader import load_enabled_skills


def _with_project_path_sandbox(
    fn: Callable[..., ToolResponse],
    project_root: Path,
    *,
    is_write_tool: bool,
) -> Callable[..., ToolResponse]:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> ToolResponse:
        if not args:
            raise ValueError("A text-file path argument is required.")

        path = str(args[0])
        safe_path = str(resolve_project_path(project_root, path))

        if is_write_tool:
            if len(args) < 2:
                raise ValueError("write_text_file requires content.")
            content = str(args[1])
            overwrite = _coerce_overwrite(kwargs.get("overwrite", False))
            ensure_writable(Path(safe_path), overwrite=overwrite)
            return fn(safe_path, content, overwrite=overwrite)

        return fn(safe_path)

    return wrapped


def _tool_signature_text(fn: Callable[..., Any]) -> str:
    return f"{fn.__name__}{inspect.signature(fn)}"


def _coerce_overwrite(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off", ""}:
            return False
        raise ValueError("overwrite must be a boolean value.")
    if isinstance(value, (int, float)):
        return bool(value)
    raise ValueError("overwrite must be a boolean value.")

def _enable_builtin_file_tools(toolkit: Toolkit, project_root: Path) -> list[str]:
    scoped_root = project_root.resolve()
    wrapped_view = _with_project_path_sandbox(
        view_text_file, scoped_root, is_write_tool=False
    )
    wrapped_write = _with_project_path_sandbox(
        write_text_file, scoped_root, is_write_tool=True
    )
    toolkit.register_tool_function(wrapped_view)
    toolkit.register_tool_function(wrapped_write)
    return [_tool_signature_text(wrapped_view), _tool_signature_text(wrapped_write)]


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
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    tool_lines.append("(plus tool functions provided by registered AgentScope skills)")
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
    response = await agent(user_msg)
    assistant_text = _normalize_response_text(response.content)
    memory_store.append(ctx.session_id, {"role": "user", "content": user_text}, user_id=ctx.user_id)
    memory_store.append(
        ctx.session_id,
        {"role": "assistant", "content": assistant_text},
        user_id=ctx.user_id,
    )
    return assistant_text
