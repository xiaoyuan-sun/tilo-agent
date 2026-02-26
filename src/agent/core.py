from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from agent.prompt_builder import build_sys_prompt
from llm.client import build_model_from_env
from memory.jsonl_store import JsonlMemoryStore
from runtime.file_access import ensure_writable, resolve_project_path
from runtime.session import SessionContext
from skills.loader import load_enabled_skills


def _load_builtin_file_tools() -> tuple[Callable[..., Any], Callable[..., Any]]:
    # Keep import strategy tolerant across AgentScope versions.
    candidates = [
        ("agentscope.tool", "view_text_file"),
        ("agentscope.tool.builtin", "view_text_file"),
        ("agentscope.tool.builtin.file_tools", "view_text_file"),
    ]
    view_tool = _load_first_attr(candidates)

    candidates = [
        ("agentscope.tool", "write_text_file"),
        ("agentscope.tool.builtin", "write_text_file"),
        ("agentscope.tool.builtin.file_tools", "write_text_file"),
    ]
    write_tool = _load_first_attr(candidates)
    return view_tool, write_tool


def _load_first_attr(candidates: list[tuple[str, str]]) -> Callable[..., Any]:
    for module_name, attr_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        value = getattr(module, attr_name, None)
        if callable(value):
            return value
    details = ", ".join(f"{mod}.{attr}" for mod, attr in candidates)
    raise RuntimeError(f"Unable to locate AgentScope builtin tool. Checked: {details}")


def _register_tool_callable(toolkit: Toolkit, fn: Callable[..., Any]) -> None:
    for method_name in ("register_tool", "register_function", "add_tool"):
        method = getattr(toolkit, method_name, None)
        if method is None:
            continue
        try:
            method(fn)
            return
        except TypeError:
            try:
                method(fn.__name__, fn)
                return
            except TypeError:
                continue
    raise RuntimeError("Toolkit does not expose a supported function registration method.")


def _wrap_project_scoped_file_tool(
    fn: Callable[..., Any],
    project_root: Path,
    *,
    is_write_tool: bool,
) -> Callable[..., Any]:
    signature = inspect.signature(fn)
    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    accepts_overwrite = "overwrite" in signature.parameters or accepts_kwargs

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

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        args_list = list(args)
        path_key = None
        raw_path = None

        if args_list and isinstance(args_list[0], str):
            raw_path = args_list[0]
        else:
            for candidate_key in ("path", "file_path", "filepath", "filename"):
                if candidate_key in kwargs and isinstance(kwargs[candidate_key], str):
                    path_key = candidate_key
                    raw_path = kwargs[candidate_key]
                    break

        if raw_path is None:
            raise ValueError("A text-file tool path argument is required.")

        safe_path = str(resolve_project_path(project_root, raw_path))
        if args_list and isinstance(args_list[0], str):
            args_list[0] = safe_path
        elif path_key is not None:
            kwargs[path_key] = safe_path

        if is_write_tool:
            overwrite = _coerce_overwrite(kwargs.get("overwrite", False))
            ensure_writable(Path(safe_path), overwrite=overwrite)
            if "overwrite" not in kwargs and accepts_overwrite:
                kwargs["overwrite"] = False

        return fn(*args_list, **kwargs)

    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped


def _enable_builtin_file_tools(toolkit: Toolkit, project_root: Path) -> None:
    view_tool, write_tool = _load_builtin_file_tools()
    _register_tool_callable(
        toolkit,
        _wrap_project_scoped_file_tool(view_tool, project_root.resolve(), is_write_tool=False),
    )
    _register_tool_callable(
        toolkit,
        _wrap_project_scoped_file_tool(write_tool, project_root.resolve(), is_write_tool=True),
    )


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
    summary_text, skill_dirs = load_enabled_skills(ctx.enabled_skills)
    toolkit = Toolkit()
    _enable_builtin_file_tools(toolkit, ctx.project_root)
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    sys_prompt = build_sys_prompt(
        summary_text,
        "view_text_file(path)\nwrite_text_file(path, content, overwrite=false)",
    )
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id)
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
    memory_store.append(ctx.session_id, {"role": "user", "content": user_text})
    memory_store.append(ctx.session_id, {"role": "assistant", "content": assistant_text})
    return assistant_text
