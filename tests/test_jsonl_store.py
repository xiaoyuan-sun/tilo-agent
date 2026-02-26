from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memory.jsonl_store import JsonlMemoryStore


class TestJsonlMemoryStore:
    def test_append_creates_file(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        store.append("session1", {"role": "user", "content": "hello"})
        assert (tmp_path / "session1.jsonl").exists()

    def test_append_persists_records_in_order(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        store.append("s1", {"role": "user", "content": "first"})
        store.append("s1", {"role": "assistant", "content": "second"})
        records = store.load("s1")
        assert len(records) == 2
        assert records[0]["content"] == "first"
        assert records[1]["content"] == "second"

    def test_load_returns_empty_for_missing_session(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        records = store.load("nonexistent")
        assert records == []

    def test_load_parses_all_lines(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        store.append("s1", {"idx": 1})
        store.append("s1", {"idx": 2})
        records = store.load("s1")
        assert [r["idx"] for r in records] == [1, 2]

    def test_load_skips_empty_lines(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        store.append("s1", {"data": "valid"})
        # Manually add an empty line
        path = tmp_path / "s1.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write("\n")
        store.append("s1", {"data": "more"})
        records = store.load("s1")
        assert len(records) == 2

    def test_load_raises_on_malformed_json(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        path = tmp_path / "bad.jsonl"
        path.write_text('{"valid": true}\nnot json at all\n', encoding="utf-8")
        with pytest.raises(Exception):  # JSONDecodeError
            store.load("bad")

    def test_creates_base_dir_if_missing(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "dirs"
        store = JsonlMemoryStore(nested)
        assert nested.exists()

    def test_handles_unicode_content(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        store.append("s1", {"content": "你好世界 🌍"})
        records = store.load("s1")
        assert records[0]["content"] == "你好世界 🌍"

    def test_separates_sessions_by_file(self, tmp_path: Path) -> None:
        store = JsonlMemoryStore(tmp_path)
        store.append("session_a", {"data": "a"})
        store.append("session_b", {"data": "b"})
        assert len(store.load("session_a")) == 1
        assert len(store.load("session_b")) == 1
        assert store.load("session_a")[0]["data"] == "a"
