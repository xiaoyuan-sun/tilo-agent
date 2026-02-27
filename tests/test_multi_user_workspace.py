from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memory.jsonl_store import JsonlMemoryStore
from runtime.file_access import resolve_user_workspace
from runtime.session import SessionContext


class MultiUserWorkspaceTests(unittest.TestCase):
    def test_resolve_user_workspace_rejects_invalid_user_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                resolve_user_workspace(Path(tmp), "../escape")

    def test_session_context_exposes_user_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = SessionContext(
                session_id="s1",
                user_id="alice",
                enabled_skills=[],
                workspace_base_dir=Path(tmp),
            )
            self.assertEqual(ctx.workspace_dir(), (Path(tmp) / "alice").resolve())

    def test_jsonl_memory_store_is_isolated_by_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            store.append("same-session", {"role": "user", "content": "alice"}, user_id="alice")
            store.append("same-session", {"role": "user", "content": "bob"}, user_id="bob")

            self.assertEqual(
                store.load("same-session", user_id="alice"),
                [{"role": "user", "content": "alice"}],
            )
            self.assertEqual(
                store.load("same-session", user_id="bob"),
                [{"role": "user", "content": "bob"}],
            )


if __name__ == "__main__":
    unittest.main()
