from __future__ import annotations

import inspect

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


async def _append_memory_entry(memory: object, entry: dict[str, str]) -> None:
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
        await _append_memory_entry(memory, entry)
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
    memory_store.append(ctx.session_id, {"role": "user", "content": user_text})
    memory_store.append(ctx.session_id, {"role": "assistant", "content": response.content})
    return response.content
