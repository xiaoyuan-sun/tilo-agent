# tests/test_stream.py
from __future__ import annotations

import asyncio
import unittest
from agent.stream import StreamEvent, StreamingHook


class StreamEventTests(unittest.TestCase):
    def test_stream_event_creation(self) -> None:
        event = StreamEvent(type="thinking", data="")
        self.assertEqual(event.type, "thinking")
        self.assertEqual(event.data, "")

    def test_stream_event_tool_call(self) -> None:
        event = StreamEvent(type="tool_call", data="time.now")
        self.assertEqual(event.type, "tool_call")
        self.assertEqual(event.data, "time.now")

    def test_stream_event_frozen(self) -> None:
        event = StreamEvent(type="thinking", data="")
        with self.assertRaises(AttributeError):
            event.data = "modified"  # type: ignore



class StreamingHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        self.hook = StreamingHook(self.queue)

    def test_pre_reasoning_emits_thinking_event(self) -> None:
        self.hook.pre_reasoning(None, {})  # type: ignore
        event = self.queue.get_nowait()
        self.assertEqual(event.type, "thinking")
        self.assertEqual(event.data, "")

    def test_pre_acting_emits_tool_call_event(self) -> None:
        self.hook.pre_acting(None, {"parsed": {"name": "time.now"}})  # type: ignore
        event = self.queue.get_nowait()
        self.assertEqual(event.type, "tool_call")
        self.assertEqual(event.data, "time.now")

    def test_pre_acting_handles_missing_parsed(self) -> None:
        self.hook.pre_acting(None, {})  # type: ignore
        event = self.queue.get_nowait()
        self.assertEqual(event.type, "tool_call")
        self.assertEqual(event.data, "unknown")


if __name__ == "__main__":
    unittest.main()
