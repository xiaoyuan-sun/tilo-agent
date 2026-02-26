from __future__ import annotations

import inspect
import json
from typing import Any, Mapping

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from agent.prompt_builder import build_sys_prompt
from llm.client import build_model_from_env
from memory.jsonl_store import JsonlMemoryStore
from runtime.session import SessionContext
from skills.loader import load_enabled_skills


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
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    sys_prompt = build_sys_prompt(summary_text, "(managed by AgentScope Toolkit)")
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
