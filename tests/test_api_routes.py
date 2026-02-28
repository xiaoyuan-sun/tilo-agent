# tests/test_api_routes.py
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
import unittest
from unittest.mock import patch, AsyncMock

import pytest

pytest.importorskip("fastapi")

from agent.stream import StreamEvent
from api.routes import app, ChatRequest
from fastapi.testclient import TestClient


async def _mock_chat_stream(
    user_text: str, ctx: object
) -> AsyncGenerator[StreamEvent, None]:
    """Mock chat_stream that yields test events."""
    yield StreamEvent("thinking", "")
    yield StreamEvent("text", "Hello, this is a test response.")
    yield StreamEvent("done", "")


class SSERoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("api.routes.chat_stream", _mock_chat_stream)
    def test_chat_stream_endpoint_returns_sse(self) -> None:
        response = self.client.post(
            "/chat/stream",
            json={"message": "hello", "session_id": "test-sse"},
            headers={"Accept": "text/event-stream"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("content-type", ""))

    @patch("api.routes.chat_stream", _mock_chat_stream)
    def test_sse_events_have_correct_format(self) -> None:
        response = self.client.post(
            "/chat/stream",
            json={"message": "hello", "session_id": "test-sse-format"},
        )

        # 读取 SSE 事件
        lines = response.text.strip().split("\n\n")
        for line in lines:
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                self.assertIn("type", payload)
                self.assertIn("data", payload)


if __name__ == "__main__":
    unittest.main()
