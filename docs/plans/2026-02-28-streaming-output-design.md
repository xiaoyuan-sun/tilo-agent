# Agent 流式输出功能设计

## 概述

为 Tilo Agent 添加流式输出能力，支持 CLI 和 API (SSE) 两种使用场景，同时暴露中间过程状态（思考中、工具调用中）。

## 需求总结

| 项目 | 决策 |
|------|------|
| 使用场景 | CLI UX + API/Service (SSE) |
| 输出方式 | Async Generator |
| 中间事件 | thinking, tool_call, text, done |
| 工具结果 | 不暴露给前端 |
| 文本输出 | 一次性输出（非逐 token） |
| 实现方式 | AgentScope Hooks |
| 向后兼容 | 保留 `run_once()`，新增 `chat_stream()` |

## 数据结构

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class StreamEvent:
    """流式输出事件"""
    type: Literal["thinking", "tool_call", "text", "done"]
    data: str  # thinking/done 时为空，tool_call 时为工具名，text 时为内容
```

事件示例：
- `StreamEvent("thinking", "")` - 正在思考
- `StreamEvent("tool_call", "time.now")` - 正在执行工具
- `StreamEvent("text", "现在时间是...")` - 最终回复文本
- `StreamEvent("done", "")` - 流结束

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      chat_stream()                          │
│  ┌─────────────┐     ┌─────────────┐     ┌──────────────┐  │
│  │ asyncio.Queue│◄────│Hooks       │     │ ReActAgent   │  │
│  │             │     │ - pre_reason│◄────│              │  │
│  │             │     │ - pre_acting│     │              │  │
│  └──────┬──────┘     └─────────────┘     └──────────────┘  │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ yield events│                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
   ┌──────────────┐
   │   Consumer   │
   ├──────────────┤
   │ - CLI        │
   │ - SSE API    │
   └──────────────┘
```

## 模块设计

### 1. 事件定义 (`src/agent/stream.py` - 新增)

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class StreamEvent:
    """流式输出事件"""
    type: Literal["thinking", "tool_call", "text", "done"]
    data: str
```

### 2. Hook 实现 (`src/agent/stream.py`)

```python
import asyncio
from typing import Any

class StreamingHook:
    """通过 hooks 收集事件，供 chat_stream 使用"""

    def __init__(self, queue: asyncio.Queue[StreamEvent | None]):
        self.queue = queue

    def pre_reasoning(self, agent: Any, kwargs: dict) -> None:
        """推理开始前，emit thinking 事件"""
        self.queue.put_nowait(StreamEvent("thinking", ""))

    def pre_acting(self, agent: Any, kwargs: dict) -> None:
        """工具执行前，emit tool_call 事件"""
        tool_name = kwargs.get("parsed", {}).get("name", "unknown")
        self.queue.put_nowait(StreamEvent("tool_call", tool_name))
```

### 3. chat_stream 主函数 (`src/agent/core.py`)

```python
import asyncio
from typing import AsyncGenerator

async def chat_stream(
    user_text: str,
    ctx: SessionContext
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

    # 构建 agent 组件（复用现有逻辑）
    toolkit, sys_prompt, memory, model = _build_agent_components(ctx)

    agent = ReActAgent(
        name="Tilo",
        sys_prompt=sys_prompt,
        model=model,
        toolkit=toolkit,
        memory=memory,
        max_iters=ctx.max_iters,
    )

    # 注册 hooks
    agent.register_instance_hook("pre_reasoning", "stream", hook.pre_reasoning)
    agent.register_instance_hook("pre_acting", "stream", hook.pre_acting)

    # 在后台任务中运行 agent
    async def run_agent():
        try:
            user_msg = Msg(name="user", content=user_text, role="user")
            response = await agent(user_msg)
            text = _normalize_response_text(response.content)
            if text:
                await queue.put(StreamEvent("text", text))
        finally:
            await queue.put(None)  # 结束信号

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

### 4. CLI 集成 (`src/runtime/cli.py`)

```python
async def chat_loop_stream(ctx: SessionContext) -> None:
    """流式 CLI 交互"""
    from agent.core import chat_stream

    print(f"Session: {ctx.session_id} | type quit to exit")

    while True:
        try:
            user_text = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return

        if not user_text:
            continue
        if user_text.lower() in {"quit", "exit"}:
            print("Bye.")
            return

        # 流式输出
        async for event in chat_stream(user_text, ctx):
            if event.type == "thinking":
                print("\n[Tilo 正在思考...]", end="", flush=True)
            elif event.type == "tool_call":
                print(f"\n[Tilo 正在调用工具: {event.data}]", end="", flush=True)
            elif event.type == "text":
                print(f"\nTilo> {event.data}")
            # done 事件无需特殊处理
```

### 5. API (SSE) 集成 (`src/api/routes.py` - 新增)

```python
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.core import chat_stream
from runtime.session import SessionContext

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    session_id: str
    skills: list[str] | None = None


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """SSE 流式接口"""
    ctx = SessionContext(
        session_id=request.session_id,
        enabled_skills=request.skills,
    )

    async def sse_generator():
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

## 多用户并行支持

每次调用 `chat_stream()` 都会创建独立的：
- `asyncio.Queue` 实例
- `StreamingHook` 实例
- `ReActAgent` 实例
- `SessionContext` 实例

因此天然支持多用户并行访问，无需额外处理。

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/agent/stream.py` | 新增 | StreamEvent, StreamingHook 定义 |
| `src/agent/core.py` | 修改 | 新增 chat_stream(), 抽取 _build_agent_components() |
| `src/runtime/cli.py` | 修改 | 新增 chat_loop_stream() |
| `src/api/routes.py` | 新增 | SSE API 端点 |

## 向后兼容性

- `run_once()` 函数保持不变
- 现有代码无需修改
- 新功能通过 `chat_stream()` 提供

## 测试计划

1. **单元测试**
   - StreamEvent 序列化/反序列化
   - StreamingHook 事件触发
   - chat_stream 事件顺序验证

2. **集成测试**
   - CLI 流式输出
   - SSE API 端点响应格式
   - 多用户并发场景

3. **手动测试**
   - 使用 curl 测试 SSE 端点
   - CLI 交互体验验证
