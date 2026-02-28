from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runtime.cli import build_context, chat_loop


class CliEntryTests(unittest.TestCase):
    def test_build_context_uses_explicit_session_and_skills(self) -> None:
        ctx = build_context(
            session_id="s1",
            skills_csv="time_skill,math_skill",
            timezone="Asia/Seoul",
            memory_dir="./data",
            max_iters=4,
        )
        self.assertEqual(ctx.session_id, "s1")
        self.assertEqual(ctx.enabled_skills, ["time_skill", "math_skill"])
        self.assertEqual(ctx.max_iters, 4)

    def test_chat_loop_runs_multi_turn_and_stops_on_quit(self) -> None:
        prompts = iter(["现在几点？", "2+2", "quit"])
        outputs: list[str] = []
        calls: list[str] = []

        def fake_input(_: str) -> str:
            return next(prompts)

        def fake_output(msg: str) -> None:
            outputs.append(msg)

        async def fake_run_once(user_text: str, _ctx) -> str:
            calls.append(user_text)
            return f"echo:{user_text}"

        ctx = build_context(
            session_id="s2",
            skills_csv="time_skill,math_skill",
            timezone="Asia/Seoul",
            memory_dir="./data",
            max_iters=6,
        )
        asyncio.run(
            chat_loop(
                ctx=ctx,
                input_fn=fake_input,
                output_fn=fake_output,
                run_once_fn=fake_run_once,
            )
        )

        self.assertEqual(calls, ["现在几点？", "2+2"])
        self.assertIn("Tilo> echo:现在几点？", outputs)
        self.assertIn("Tilo> echo:2+2", outputs)

    def test_build_context_defaults_to_all_builtin_skills_when_empty(self) -> None:
        with patch("runtime.cli.scan_builtin_skills", return_value=["time_skill", "math_skill"]):
            ctx = build_context(
                session_id="s3",
                skills_csv="",
                timezone="Asia/Seoul",
                memory_dir="./data",
                max_iters=6,
            )
        self.assertEqual(ctx.enabled_skills, ["time_skill", "math_skill"])


# tests/test_cli_entry.py - 追加测试

from typing import AsyncGenerator
from agent.stream import StreamEvent
from runtime.session import SessionContext


def test_chat_loop_stream_calls_output_fn() -> None:
    outputs: list[str] = []
    ctx = SessionContext(session_id="test-stream-cli", enabled_skills=["time_skill"])

    inputs = iter(["hello", "quit"])

    async def fake_chat_stream(
        user_text: str, _ctx: SessionContext
    ) -> AsyncGenerator[StreamEvent, None]:
        """Mock chat_stream that yields test events"""
        yield StreamEvent("thinking", "")
        yield StreamEvent("text", f"echo:{user_text}")
        yield StreamEvent("done", "")

    async def run_test() -> None:
        from runtime.cli import chat_loop_stream
        with patch("agent.core.chat_stream", side_effect=fake_chat_stream):
            await chat_loop_stream(
                ctx,
                input_fn=lambda _: next(inputs),
                output_fn=outputs.append,
            )

    asyncio.run(run_test())

    # 应该有 session 信息输出
    assert any("Session" in o for o in outputs)
    # 应该有 thinking 输出
    assert any("Tilo 正在思考" in o for o in outputs)
    # 应该有 text 输出
    assert any("echo:hello" in o for o in outputs)
    # 应该有 "Bye." 输出
    assert any("Bye" in o for o in outputs)


if __name__ == "__main__":
    unittest.main()
