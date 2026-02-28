from __future__ import annotations

import asyncio
import os
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from agent.core import chat_stream
from agent.stream import StreamEvent
from llm.client import MockModel
from runtime.session import SessionContext


class ChatStreamTests(unittest.TestCase):
    @patch("agent.core.build_model_from_env")
    def test_chat_stream_yields_events(self, mock_build_model: object) -> None:
        mock_build_model.return_value = MockModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = SessionContext(
                session_id="test-stream",
                enabled_skills=["time_skill"],
                memory_dir=Path(tmpdir),
            )

            async def collect_events() -> list[StreamEvent]:
                events = []
                async for event in chat_stream("现在几点？", ctx):
                    events.append(event)
                return events

            events = asyncio.run(collect_events())

            # 应该至少有 thinking, tool_call, text, done
            event_types = [e.type for e in events]
            self.assertIn("thinking", event_types)
            self.assertIn("done", event_types)
            # 最后一个事件应该是 done
            self.assertEqual(events[-1].type, "done")

    @patch("agent.core.build_model_from_env")
    def test_chat_stream_text_event_has_content(self, mock_build_model: object) -> None:
        mock_build_model.return_value = MockModel()
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = SessionContext(
                session_id="test-stream-2",
                enabled_skills=["time_skill"],
                memory_dir=Path(tmpdir),
            )

            async def collect_events() -> list[StreamEvent]:
                events = []
                async for event in chat_stream("现在几点？", ctx):
                    events.append(event)
                return events

            events = asyncio.run(collect_events())

            text_events = [e for e in events if e.type == "text"]
            if text_events:
                # 如果有 text 事件，data 应该非空
                self.assertTrue(len(text_events[0].data) > 0)


if __name__ == "__main__":
    unittest.main()
