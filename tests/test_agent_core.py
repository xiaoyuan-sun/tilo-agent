from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.tool import Toolkit

from agent.core import (
    _append_memory_entry,
    _build_agent_components,
    _history_entry_to_msg,
    _normalize_response_text,
)
from runtime.session import SessionContext


class _AsyncAddMemory:
    def __init__(self) -> None:
        self.records: list[Msg] = []

    async def add(self, record: Msg) -> None:
        self.records.append(record)


class AgentCoreTests(unittest.TestCase):
    def test_history_entry_to_msg_converts_dict(self) -> None:
        msg = _history_entry_to_msg({"role": "user", "content": "hello"})
        self.assertIsInstance(msg, Msg)
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "hello")

    def test_history_entry_to_msg_passthrough_msg(self) -> None:
        original = Msg(name="assistant", role="assistant", content="ok")
        converted = _history_entry_to_msg(original)
        self.assertIs(converted, original)

    def test_append_memory_entry_with_async_add_receives_msg(self) -> None:
        memory = _AsyncAddMemory()
        msg = Msg(name="user", role="user", content="hi")
        asyncio.run(_append_memory_entry(memory, msg))
        self.assertEqual(len(memory.records), 1)
        self.assertIs(memory.records[0], msg)

    def test_normalize_response_text_from_structured_blocks(self) -> None:
        content = [{"type": "text", "text": "line1"}, {"type": "text", "text": "line2"}]
        self.assertEqual(_normalize_response_text(content), "line1\nline2")

    def test_normalize_response_text_falls_back_to_json(self) -> None:
        content = [{"type": "tool_use", "name": "time.now", "input": {}}]
        self.assertEqual(_normalize_response_text(content), json.dumps(content, ensure_ascii=False))


class BuildAgentComponentsTests(unittest.TestCase):
    def test_build_agent_components_returns_tuple(self) -> None:
        ctx = SessionContext(session_id="test", enabled_skills=["time_skill"])
        toolkit, sys_prompt, memory, model = _build_agent_components(ctx)
        self.assertIsNotNone(toolkit)
        self.assertIsInstance(sys_prompt, str)
        self.assertIsNotNone(memory)
        self.assertIsNotNone(model)


if __name__ == "__main__":
    unittest.main()
