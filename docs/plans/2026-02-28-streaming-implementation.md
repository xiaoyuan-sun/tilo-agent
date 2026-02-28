# Agent 流式输出功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Tilo Agent 添加流式输出能力，支持 CLI 和 API (SSE) 两种场景，暴露中间过程状态。

**Architecture:** 使用 AgentScope Hooks 机制（pre_reasoning, pre_acting）捕获中间状态，通过 asyncio.Queue 连接 hooks 和 AsyncGenerator，实现解耦的流式输出。

**Tech Stack:** AgentScope, asyncio, dataclasses, FastAPI (SSE)

---

## Task 1: 创建 StreamEvent 数据结构

**Files:**
- Create: `src/agent/stream.py`
- Test: `tests/test_stream.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_stream.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.stream'"

**Step 3: Write minimal implementation**

```python
# src/agent/stream.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class StreamEvent:
    """流式输出事件"""
    type: Literal["thinking", "tool_call", "text", "done"]
    data: str
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_stream.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/agent/stream.py tests/test_stream.py
git commit -m "feat: add StreamEvent dataclass for streaming output"
```

---

## Task 2: 实现 StreamingHook 类

**Files:**
- Modify: `src/agent/stream.py`
- Modify: `tests/test_stream.py`

**Step 1: Write the failing test**

```python
# tests/test_stream.py - 追加以下测试类

import asyncio
from agent.stream import StreamingHook


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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_stream.py::StreamingHookTests -v`
Expected: FAIL with "AttributeError: module 'agent.stream' has no attribute 'StreamingHook'"

**Step 3: Write minimal implementation**

```python
# src/agent/stream.py - 追加以下代码

import asyncio
from typing import Any


class StreamingHook:
    """通过 hooks 收集事件，供 chat_stream 使用"""

    def __init__(self, queue: asyncio.Queue[StreamEvent | None]) -> None:
        self.queue = queue

    def pre_reasoning(self, agent: Any, kwargs: dict[str, Any]) -> None:
        """推理开始前，emit thinking 事件"""
        self.queue.put_nowait(StreamEvent("thinking", ""))

    def pre_acting(self, agent: Any, kwargs: dict[str, Any]) -> None:
        """工具执行前，emit tool_call 事件"""
        tool_name = kwargs.get("parsed", {}).get("name", "unknown")
        self.queue.put_nowait(StreamEvent("tool_call", str(tool_name)))
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_stream.py -v`
Expected: PASS (6 tests total)

**Step 5: Commit**

```bash
git add src/agent/stream.py tests/test_stream.py
git commit -m "feat: add StreamingHook class for capturing agent events"
```

---

## Task 3: 抽取 _build_agent_components 辅助函数

**Files:**
- Modify: `src/agent/core.py`
- Modify: `tests/test_agent_core.py`

**Step 1: Write the failing test**

```python
# tests/test_agent_core.py - 追加导入和测试

from agent.core import _build_agent_components, run_once
from runtime.session import SessionContext


class BuildAgentComponentsTests(unittest.TestCase):
    def test_build_agent_components_returns_tuple(self) -> None:
        ctx = SessionContext(session_id="test", enabled_skills=["time_skill"])
        toolkit, sys_prompt, memory, model = _build_agent_components(ctx)
        self.assertIsNotNone(toolkit)
        self.assertIsInstance(sys_prompt, str)
        self.assertIsNotNone(memory)
        self.assertIsNotNone(model)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_agent_core.py::BuildAgentComponentsTests -v`
Expected: FAIL with "cannot import name '_build_agent_components'"

**Step 3: Refactor run_once to extract helper function**

```python
# src/agent/core.py - 修改文件

# 在 run_once 函数之前添加:

def _build_agent_components(
    ctx: SessionContext,
) -> tuple[Toolkit, str, InMemoryMemory, BaseModel]:
    """构建 agent 所需的组件，供 run_once 和 chat_stream 复用"""
    _, skill_dirs = load_enabled_skills(ctx.enabled_skills)
    toolkit = Toolkit()
    _enable_builtin_file_tools(toolkit, ctx.project_root)
    # Note: MCP auto-registration 需要在调用方处理，因为它需要 async
    for skill_dir in skill_dirs:
        toolkit.register_agent_skill(str(skill_dir))
    prompt_context = compose_prompt_context(ctx.workspace_dir())
    sys_prompt = build_sys_prompt(prompt_context, "(tool functions registered)")
    memory = InMemoryMemory()
    model = build_model_from_env()
    return toolkit, sys_prompt, memory, model


# 修改 run_once 函数，复用 _build_agent_components:
async def run_once(user_text: str, ctx: SessionContext) -> str:
    toolkit, sys_prompt, memory, model = _build_agent_components(ctx)

    # MCP registration (需要 async)
    mcp_manager = await auto_register_mcp_clients(toolkit)

    agent = ReActAgent(
        name="Tilo",
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=memory,
        max_iters=ctx.max_iters,
    )
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id, user_id=ctx.user_id)
    for entry in history:
        await _append_memory_entry(memory, _history_entry_to_msg(entry))

    user_msg = Msg(name="user", content=user_text, role="user")
    try:
        response = await agent(user_msg)
        assistant_text = _normalize_response_text(response.content)
        memory_store.append(
            ctx.session_id, {"role": "user", "content": user_text}, user_id=ctx.user_id
        )
        memory_store.append(
            ctx.session_id,
            {"role": "assistant", "content": assistant_text},
            user_id=ctx.user_id,
        )
        return assistant_text
    finally:
        await mcp_manager.close()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_agent_core.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent/core.py tests/test_agent_core.py
git commit -m "refactor: extract _build_agent_components helper function"
```

---

## Task 4: 实现 chat_stream 函数

**Files:**
- Modify: `src/agent/core.py`
- Create: `tests/test_chat_stream.py`

**Step 1: Write the failing test**

```python
# tests/test_chat_stream.py
from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
import tempfile

from agent.core import chat_stream
from agent.stream import StreamEvent
from runtime.session import SessionContext


class ChatStreamTests(unittest.TestCase):
    def test_chat_stream_yields_events(self) -> None:
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

    def test_chat_stream_text_event_has_content(self) -> None:
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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_chat_stream.py -v`
Expected: FAIL with "cannot import name 'chat_stream'"

**Step 3: Write implementation**

```python
# src/agent/core.py - 追加导入和函数

from typing import AsyncGenerator
from agent.stream import StreamEvent, StreamingHook


async def chat_stream(
    user_text: str,
    ctx: SessionContext,
) -> AsyncGenerator[StreamEvent, None]:
    """流式对话接口

    Args:
        user_text: 用户输入
        ctx: 会话上下文

    Yields:
        StreamEvent: 流式事件（thinking, tool_call, text, done）
    """
    queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
    hook = StreamingHook(queue)

    toolkit, sys_prompt, memory, model = _build_agent_components(ctx)
    mcp_manager = await auto_register_mcp_clients(toolkit)

    agent = ReActAgent(
        name="Tilo",
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=memory,
        max_iters=ctx.max_iters,
    )

    # 注册 hooks
    agent.register_instance_hook("pre_reasoning", "stream", hook.pre_reasoning)
    agent.register_instance_hook("pre_acting", "stream", hook.pre_acting)

    # 加载历史记忆
    memory_store = JsonlMemoryStore(ctx.memory_dir)
    history = memory_store.load(ctx.session_id, user_id=ctx.user_id)
    for entry in history:
        await _append_memory_entry(memory, _history_entry_to_msg(entry))

    # 在后台任务中运行 agent
    async def run_agent() -> None:
        try:
            user_msg = Msg(name="user", content=user_text, role="user")
            response = await agent(user_msg)
            text = _normalize_response_text(response.content)
            if text:
                await queue.put(StreamEvent("text", text))

            # 保存对话历史
            memory_store.append(
                ctx.session_id,
                {"role": "user", "content": user_text},
                user_id=ctx.user_id,
            )
            memory_store.append(
                ctx.session_id,
                {"role": "assistant", "content": text},
                user_id=ctx.user_id,
            )
        finally:
            await queue.put(None)
            await mcp_manager.close()

    task = asyncio.create_task(run_agent())

    # 消费队列，yield 事件
    while True:
        event = await queue.get()
        if event is None:
            break
        yield event

    yield StreamEvent("done", "")
    await task  # 确保异常被传播
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_chat_stream.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent/core.py tests/test_chat_stream.py
git commit -m "feat: add chat_stream async generator for streaming output"
```

---

## Task 5: 实现 CLI 流式输出

**Files:**
- Modify: `src/runtime/cli.py`
- Modify: `tests/test_cli_entry.py`

**Step 1: Write the failing test**

```python
# tests/test_cli_entry.py - 追加测试

import asyncio
from runtime.cli import chat_loop_stream
from runtime.session import SessionContext


def test_chat_loop_stream_calls_output_fn() -> None:
    outputs: list[str] = []
    ctx = SessionContext(session_id="test-stream-cli", enabled_skills=["time_skill"])

    inputs = iter(["hello", "quit"])

    async def run_test() -> None:
        await chat_loop_stream(
            ctx,
            input_fn=lambda _: next(inputs),
            output_fn=outputs.append,
        )

    asyncio.run(run_test())

    # 应该有 session 信息输出
    assert any("Session" in o for o in outputs)
    # 应该有 "Bye." 输出
    assert any("Bye" in o for o in outputs)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_cli_entry.py::test_chat_loop_stream_calls_output_fn -v`
Expected: FAIL with "cannot import name 'chat_loop_stream'"

**Step 3: Write implementation**

```python
# src/runtime/cli.py - 追加函数

async def chat_loop_stream(
    ctx: SessionContext,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """流式 CLI 交互"""
    from agent.core import chat_stream

    output_fn(
        f"Session: {ctx.session_id} | skills={','.join(ctx.enabled_skills)} | type quit to exit"
    )

    while True:
        try:
            user_text = input_fn("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("\nBye.")
            return

        if not user_text:
            continue
        if user_text.lower() in {"quit", "exit"}:
            output_fn("Bye.")
            return

        # 流式输出
        async for event in chat_stream(user_text, ctx):
            if event.type == "thinking":
                output_fn("[Tilo 正在思考...]")
            elif event.type == "tool_call":
                output_fn(f"[Tilo 正在调用工具: {event.data}]")
            elif event.type == "text":
                output_fn(f"Tilo> {event.data}")
            # done 事件无需特殊处理
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_cli_entry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/runtime/cli.py tests/test_cli_entry.py
git commit -m "feat: add chat_loop_stream for CLI streaming output"
```

---

## Task 6: 实现 SSE API 端点

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/routes.py`
- Create: `tests/test_api_routes.py`

**Step 1: Write the failing test**

```python
# tests/test_api_routes.py
from __future__ import annotations

import asyncio
import json
import unittest

import pytest

pytest.importorskip("fastapi")

from api.routes import app, ChatRequest
from fastapi.testclient import TestClient


class SSERoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_chat_stream_endpoint_returns_sse(self) -> None:
        response = self.client.post(
            "/chat/stream",
            json={"message": "hello", "session_id": "test-sse"},
            headers={"Accept": "text/event-stream"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("content-type", ""))

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
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_api_routes.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'api'"

**Step 3: Write implementation**

```python
# src/api/__init__.py
from api.routes import app

__all__ = ["app"]
```

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/test_api_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/api/__init__.py src/api/routes.py tests/test_api_routes.py
git commit -m "feat: add SSE streaming API endpoint"
```

---

## Task 7: 运行完整测试套件

**Step 1: Run all tests**

Run: `cd /Users/yuan/Project/AI/tilo-agent && PYTHONPATH=src pytest tests/ -v`
Expected: All tests PASS

**Step 2: Fix any failures**

如果有测试失败，逐个修复直到全部通过。

---

## Task 8: 更新 pyproject.toml (可选)

如果需要 FastAPI 依赖，添加到可选依赖：

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
api = ["fastapi>=0.100", "uvicorn>=0.23"]
```

---

## 完成检查清单

- [ ] StreamEvent 数据结构
- [ ] StreamingHook 类
- [ ] _build_agent_components 辅助函数
- [ ] chat_stream 函数
- [ ] CLI 流式输出 (chat_loop_stream)
- [ ] SSE API 端点
- [ ] 所有测试通过
- [ ] 文档更新 (README.md)
