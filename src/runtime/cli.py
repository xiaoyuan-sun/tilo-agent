from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Sequence

from runtime.session import SessionContext, new_session_id
from skills.loader import scan_builtin_skills


def build_context(
    session_id: str | None,
    skills_csv: str,
    timezone: str,
    memory_dir: str,
    max_iters: int,
) -> SessionContext:
    skills = [item.strip() for item in skills_csv.split(",") if item.strip()]
    if not skills:
        skills = scan_builtin_skills()
    if not skills:
        raise ValueError("No builtin skills found. Provide skills via --skills.")
    return SessionContext(
        session_id=session_id or new_session_id(),
        enabled_skills=skills,
        timezone=timezone,
        memory_dir=Path(memory_dir),
        max_iters=max_iters,
    )


async def chat_loop(
    ctx: SessionContext,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    run_once_fn: Callable[[str, SessionContext], Awaitable[str]] | None = None,
) -> None:
    if run_once_fn is None:
        from agent.core import run_once as run_once_fn

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

        reply = await run_once_fn(user_text, ctx)
        output_fn(f"Tilo> {reply}")


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start interactive Tilo chat.")
    parser.add_argument("--session-id", default=None, help="Reuse an existing session id.")
    parser.add_argument(
        "--skills",
        default="",
        help="Comma-separated skill names. Default: all builtin skills",
    )
    parser.add_argument("--timezone", default="Asia/Seoul")
    parser.add_argument("--memory-dir", default="./data")
    parser.add_argument("--max-iters", type=int, default=6)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    ctx = build_context(
        session_id=args.session_id,
        skills_csv=args.skills,
        timezone=args.timezone,
        memory_dir=args.memory_dir,
        max_iters=args.max_iters,
    )
    asyncio.run(chat_loop(ctx))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
