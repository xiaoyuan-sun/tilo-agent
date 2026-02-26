from __future__ import annotations

from agentscope.agent import ReActAgent
from agentscope.message import Msg
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit

from agent.prompt_builder import build_sys_prompt
from llm.client import build_model_from_env
from memory.jsonl_store import JsonlMemoryStore
from runtime.session import SessionContext
from skills.loader import load_enabled_skills


async def run_once(user_text: str, ctx: SessionContext) -> str:
    summary_text, skill_dirs = load_enabled_skills(ctx.enabled_skills)
    toolkit = Toolkit()
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    sys_prompt = build_sys_prompt(summary_text, "(managed by AgentScope Toolkit)")
    ctx.workspace_dir()
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id, user_id=ctx.user_id)
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
    memory_store.append(ctx.session_id, {"role": "user", "content": user_text}, user_id=ctx.user_id)
    memory_store.append(
        ctx.session_id,
        {"role": "assistant", "content": response.content},
        user_id=ctx.user_id,
    )
    return response.content
