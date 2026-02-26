from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memory.jsonl_store import JsonlMemoryStore


class JsonlMemoryStoreTests(unittest.TestCase):
    def test_init_creates_directory(self) -> None:
        """Verify __init__ creates the base directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "new_dir"
            self.assertFalse(base.exists())
            JsonlMemoryStore(base)
            self.assertTrue(base.exists())

    def test_append_creates_file(self) -> None:
        """Verify append() creates a new file for the session."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            store.append("session_1", {"role": "user", "content": "hello"})
            file_path = Path(tmp) / "session_1.jsonl"
            self.assertTrue(file_path.exists())

    def test_append_writes_json_line(self) -> None:
        """Verify append() writes valid JSON line to file."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            record = {"role": "user", "content": "hello"}
            store.append("session_1", record)

            file_path = Path(tmp) / "session_1.jsonl"
            content = file_path.read_text(encoding="utf-8").strip()
            loaded = json.loads(content)
            self.assertEqual(loaded, record)

    def test_append_multiple_records(self) -> None:
        """Verify multiple append() calls write multiple lines."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            store.append("session_1", {"role": "user", "content": "hello"})
            store.append("session_1", {"role": "assistant", "content": "hi there"})

            file_path = Path(tmp) / "session_1.jsonl"
            lines = file_path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0]), {"role": "user", "content": "hello"})
            self.assertEqual(json.loads(lines[1]), {"role": "assistant", "content": "hi there"})

    def test_load_returns_empty_list_for_nonexistent_file(self) -> None:
        """Verify load() returns empty list when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            result = store.load("nonexistent_session")
            self.assertEqual(result, [])

    def test_load_returns_all_records(self) -> None:
        """Verify load() returns all records from the file."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            records = [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "how are you?"},
            ]
            for record in records:
                store.append("session_1", record)

            loaded = store.load("session_1")
            self.assertEqual(loaded, records)

    def test_load_handles_unicode(self) -> None:
        """Verify load() handles Unicode characters correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            record = {"role": "user", "content": "你好世界 🌍"}
            store.append("session_1", record)

            loaded = store.load("session_1")
            self.assertEqual(loaded, [record])

    def test_multiple_sessions_isolated(self) -> None:
        """Verify different sessions are stored in separate files."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            store.append("session_a", {"data": "a1"})
            store.append("session_b", {"data": "b1"})
            store.append("session_a", {"data": "a2"})

            self.assertEqual(store.load("session_a"), [{"data": "a1"}, {"data": "a2"}])
            self.assertEqual(store.load("session_b"), [{"data": "b1"}])

    def test_default_base_dir(self) -> None:
        """Verify default base_dir is cwd/data."""
        with tempfile.TemporaryDirectory() as tmp:
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                store = JsonlMemoryStore()
                expected = Path(tmp) / "data"
                # Use resolve() to handle macOS /var -> /private/var symlink
                self.assertEqual(store.base_dir.resolve(), expected.resolve())
                self.assertTrue(expected.exists())
            finally:
                os.chdir(old_cwd)

    def test_append_preserves_record_structure(self) -> None:
        """Verify append/load preserves nested record structures."""
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonlMemoryStore(Path(tmp))
            record = {
                "role": "tool",
                "content": "result",
                "metadata": {
                    "tool_name": "calc",
                    "args": {"x": 1, "y": 2}
                }
            }
            store.append("session_1", record)
            loaded = store.load("session_1")
            self.assertEqual(loaded[0], record)


if __name__ == "__main__":
    unittest.main()
