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


if __name__ == "__main__":
    unittest.main()
