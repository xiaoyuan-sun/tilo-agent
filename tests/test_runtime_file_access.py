from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runtime.file_access import ensure_writable, resolve_project_path, resolve_user_workspace


class RuntimeFileAccessTests(unittest.TestCase):
    def test_resolve_project_path_allows_relative_file_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolved = resolve_project_path(root, "notes/todo.txt")
            self.assertEqual(resolved, (root / "notes" / "todo.txt").resolve())

    def test_resolve_project_path_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                resolve_project_path(root, "../outside.txt")

    def test_ensure_writable_rejects_existing_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.txt"
            target.write_text("x", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                ensure_writable(target, overwrite=False)

    def test_ensure_writable_allows_existing_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.txt"
            target.write_text("x", encoding="utf-8")
            ensure_writable(target, overwrite=True)

    def test_resolve_user_workspace_builds_isolated_path_per_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "workspaces"
            alice = resolve_user_workspace(base, "alice")
            bob = resolve_user_workspace(base, "bob")
            self.assertEqual(alice, (base / "alice").resolve())
            self.assertEqual(bob, (base / "bob").resolve())
            self.assertNotEqual(alice, bob)
            self.assertTrue(alice.exists())
            self.assertTrue(bob.exists())


if __name__ == "__main__":
    unittest.main()
