# tests/test_stream.py
from __future__ import annotations

import unittest
from agent.stream import StreamEvent


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


if __name__ == "__main__":
    unittest.main()
