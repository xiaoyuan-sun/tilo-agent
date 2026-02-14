from __future__ import annotations

from typing import Any

from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory

from agent.prompt_builder import build_sys_prompt
from llm.client import build_model_from_env
from memory.jsonl_store import JsonlMemoryStore
from runtime.session import SessionContext
from skills.loader import load_enabled_skills
from tools.registry import ToolRegistry


async def run_once(user_text: str, ctx: SessionContext) -> str:
    summary_text, tools = load_enabled_skills(ctx.enabled_skills)
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    tool_list = registry.list_for_prompt()
    sys_prompt = build_sys_prompt(summary_text, tool_list)
    toolkit = registry.to_agentscope_toolkit()
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id)
    memory = InMemoryMemory()
    for entry in history:
        memory.append(entry)
    model = build_model_from_env()
    agent = ReActAgent(
        name="Tilo",
        sys_prompt=sys_prompt,
        model=model,
        toolkit=toolkit,
        memory=memory,
        max_iters=ctx.max_iters,
    )
    user_msg = Msg(name="user", content=user_text, role="user")
    response = await agent.run(user_msg)
    memory_store.append(ctx.session_id, {"role": "user", "content": user_text})
    memory_store.append(ctx.session_id, {"role": "assistant", "content": response.content})
    return response.content
