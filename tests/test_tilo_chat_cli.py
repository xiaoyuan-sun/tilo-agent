from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class TiloChatCliTests(unittest.TestCase):
    def test_main_runs_single_message_mode(self) -> None:
        import tilo_chat

        captured: dict[str, object] = {}

        async def fake_run_once(user_text, ctx):
            captured["user_text"] = user_text
            captured["ctx"] = ctx
            return "reply: hello"

        out = io.StringIO()
        with patch("tilo_chat._run_once", new=fake_run_once), patch(
            "tilo_chat.new_session_id", return_value="sess-1"
        ):
            code = tilo_chat.main(
                argv=[
                    "--message",
                    "hi",
                    "--skills",
                    "time_skill,math_skill",
                ],
                stdin=io.StringIO(""),
                stdout=out,
            )

        self.assertEqual(code, 0)
        self.assertEqual(captured["user_text"], "hi")
        ctx = captured["ctx"]
        self.assertEqual(ctx.session_id, "sess-1")
        self.assertEqual(ctx.enabled_skills, ["time_skill", "math_skill"])
        self.assertIn("reply: hello", out.getvalue())

    def test_main_runs_repl_and_stops_on_exit(self) -> None:
        import tilo_chat

        calls: list[str] = []

        async def fake_run_once(user_text, ctx):
            calls.append(user_text)
            return f"reply: {user_text}"

        out = io.StringIO()
        with patch("tilo_chat._run_once", new=fake_run_once), patch(
            "tilo_chat.new_session_id", return_value="sess-2"
        ):
            code = tilo_chat.main(
                argv=["--skills", "time_skill"],
                stdin=io.StringIO("hello\nexit\n"),
                stdout=out,
            )

        self.assertEqual(code, 0)
        self.assertEqual(calls, ["hello"])
        self.assertIn("reply: hello", out.getvalue())

    def test_main_returns_error_code_for_runtime_error(self) -> None:
        import tilo_chat

        async def fake_run_once(user_text, ctx):
            raise RuntimeError("boom")

        err = io.StringIO()
        with patch("tilo_chat._run_once", new=fake_run_once):
            code = tilo_chat.main(
                argv=["--message", "hi"],
                stdin=io.StringIO(""),
                stdout=io.StringIO(),
                stderr=err,
            )

        self.assertEqual(code, 2)
        self.assertIn("boom", err.getvalue())


if __name__ == "__main__":
    unittest.main()
