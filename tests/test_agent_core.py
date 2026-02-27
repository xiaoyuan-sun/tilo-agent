from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agentscope.message import Msg

from agent.core import (
    _append_memory_entry,
    _history_entry_to_msg,
    _normalize_response_text,
    _with_project_path_sandbox,
)


class _AsyncAddMemory:
    def __init__(self) -> None:
        self.records: list[Msg] = []

    async def add(self, record: Msg) -> None:
        self.records.append(record)


class AgentCoreTests(unittest.TestCase):
    def test_with_project_path_sandbox_accepts_file_path_kwarg_for_read(self) -> None:
        captured: dict[str, object] = {}

        def fake_read(file_path: str, ranges: list[int] | None = None) -> dict[str, object]:
            captured["file_path"] = file_path
            captured["ranges"] = ranges
            return {}

        wrapped = _with_project_path_sandbox(fake_read, Path("."), is_write_tool=False)
        wrapped(file_path="README.md")

        self.assertTrue(str(captured["file_path"]).endswith("README.md"))
        self.assertIsNone(captured["ranges"])

    def test_with_project_path_sandbox_passes_ranges_for_read(self) -> None:
        captured: dict[str, object] = {}

        def fake_read(file_path: str, ranges: list[int] | None = None) -> dict[str, object]:
            captured["file_path"] = file_path
            captured["ranges"] = ranges
            return {}

        wrapped = _with_project_path_sandbox(fake_read, Path("."), is_write_tool=False)
        wrapped(file_path="README.md", ranges=[1, 5])

        self.assertEqual(captured["ranges"], [1, 5])

    def test_with_project_path_sandbox_supports_write_kwargs_and_overwrite_check(self) -> None:
        captured: dict[str, object] = {}

        def fake_write(
            file_path: str,
            content: str,
            ranges: list[int] | None = None,
        ) -> dict[str, object]:
            captured["file_path"] = file_path
            captured["content"] = content
            captured["ranges"] = ranges
            return {}

        wrapped = _with_project_path_sandbox(fake_write, Path("."), is_write_tool=True)
        wrapped(file_path="tests/tmp_write.txt", content="hello", overwrite=True, ranges=[2, 3])

        self.assertTrue(str(captured["file_path"]).endswith("tests/tmp_write.txt"))
        self.assertEqual(captured["content"], "hello")
        self.assertEqual(captured["ranges"], [2, 3])

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


if __name__ == "__main__":
    unittest.main()
