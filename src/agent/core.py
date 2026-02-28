from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any, AsyncGenerator, Callable, Mapping

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.tool import ToolResponse, Toolkit, view_text_file, write_text_file

from agent.prompt_builder import build_sys_prompt
from agent.prompt_files import compose_prompt_context
from agent.stream import StreamEvent, StreamingHook
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


def _build_agent_components(
    ctx: SessionContext,
) -> tuple[Toolkit, str, InMemoryMemory, Any]:
    """Build the core agent components: toolkit, system prompt, memory, and model.

    This function extracts the synchronous component-building logic from run_once
    to enable reuse in streaming contexts.

    Args:
        ctx: The session context containing configuration.

    Returns:
        A tuple of (toolkit, sys_prompt, memory, model).
    """
    _, skill_dirs = load_enabled_skills(ctx.enabled_skills)
    toolkit = Toolkit()
    tool_lines = _enable_builtin_file_tools(toolkit, ctx.project_root)
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    tool_lines.append("(plus tool functions provided by registered AgentScope skills)")
    prompt_context = compose_prompt_context(ctx.workspace_dir())
    sys_prompt = build_sys_prompt(prompt_context, "\n".join(tool_lines))
    memory = InMemoryMemory()
    model = build_model_from_env()
    return toolkit, sys_prompt, memory, model


async def run_once(user_text: str, ctx: SessionContext) -> str:
    toolkit, sys_prompt, memory, model = _build_agent_components(ctx)
    mcp_manager = await auto_register_mcp_clients(toolkit)
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id, user_id=ctx.user_id)
    for entry in history:
        await _append_memory_entry(memory, _history_entry_to_msg(entry))
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


async def chat_stream(
    user_text: str,
    ctx: SessionContext,
) -> AsyncGenerator[StreamEvent, None]:
    """流式对话接口

    Args:
        user_text: 用户输入
        ctx: 会话上下文

    Yields:
        StreamEvent: 流式事件（thinking, tool_call, text, done）
    """
    queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
    hook = StreamingHook(queue)

    toolkit, sys_prompt, memory, model = _build_agent_components(ctx)
    mcp_manager = await auto_register_mcp_clients(toolkit)

    agent = ReActAgent(
        name="Tilo",
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=memory,
        max_iters=ctx.max_iters,
    )

    # 注册 hooks
    agent.register_instance_hook("pre_reasoning", "stream", hook.pre_reasoning)
    agent.register_instance_hook("pre_acting", "stream", hook.pre_acting)

    # 加载历史记忆
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id, user_id=ctx.user_id)
    for entry in history:
        await _append_memory_entry(memory, _history_entry_to_msg(entry))

    # 在后台任务中运行 agent
    async def run_agent() -> None:
        try:
            user_msg = Msg(name="user", content=user_text, role="user")
            response = await agent(user_msg)
            text = _normalize_response_text(response.content)
            if text:
                await queue.put(StreamEvent("text", text))

            # 保存对话历史
            memory_store.append(
                ctx.session_id,
                {"role": "user", "content": user_text},
                user_id=ctx.user_id,
            )
            memory_store.append(
                ctx.session_id,
                {"role": "assistant", "content": text},
                user_id=ctx.user_id,
            )
        finally:
            await queue.put(None)
            await mcp_manager.close()

    task = asyncio.create_task(run_agent())

    # 消费队列，yield 事件
    while True:
        event = await queue.get()
        if event is None:
            break
        yield event

    yield StreamEvent("done", "")
    await task  # 确保异常被传播
