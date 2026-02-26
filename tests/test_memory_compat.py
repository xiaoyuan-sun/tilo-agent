from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent.core import _append_memory_entry


class _AddOnlyMemory:
    def __init__(self) -> None:
        self.records: list[dict[str, str]] = []

    def add(self, record: dict[str, str]) -> None:
        self.records.append(record)


class _AppendOnlyMemory:
    def __init__(self) -> None:
        self.records: list[dict[str, str]] = []

    def append(self, record: dict[str, str]) -> None:
        self.records.append(record)


class _AsyncAddMemory:
    def __init__(self) -> None:
        self.records: list[dict[str, str]] = []

    async def add(self, record: dict[str, str]) -> None:
        self.records.append(record)


class MemoryCompatTests(unittest.TestCase):
    def test_append_memory_entry_falls_back_to_add(self) -> None:
        memory = _AddOnlyMemory()
        asyncio.run(_append_memory_entry(memory, {"role": "user", "content": "hi"}))
        self.assertEqual(memory.records, [{"role": "user", "content": "hi"}])

    def test_append_memory_entry_prefers_append(self) -> None:
        memory = _AppendOnlyMemory()
        asyncio.run(_append_memory_entry(memory, {"role": "assistant", "content": "ok"}))
        self.assertEqual(memory.records, [{"role": "assistant", "content": "ok"}])

    def test_append_memory_entry_awaits_async_add(self) -> None:
        memory = _AsyncAddMemory()
        asyncio.run(_append_memory_entry(memory, {"role": "user", "content": "async"}))
        self.assertEqual(memory.records, [{"role": "user", "content": "async"}])


if __name__ == "__main__":
    unittest.main()
