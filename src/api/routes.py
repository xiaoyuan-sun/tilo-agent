# src/api/routes.py
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.core import chat_stream
from runtime.session import SessionContext

app = FastAPI(title="Tilo Agent API")


class ChatRequest(BaseModel):
    message: str
    session_id: str
    skills: list[str] | None = None


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """SSE 流式接口"""
    ctx = SessionContext(
        session_id=request.session_id,
        enabled_skills=request.skills,
    )

    async def sse_generator() -> Any:
        async for event in chat_stream(request.message, ctx):
            payload = {"type": event.type, "data": event.data}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
