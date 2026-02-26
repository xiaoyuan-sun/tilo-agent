from __future__ import annotations

import unittest
from pathlib import Path


class NoLegacyToolRefsTests(unittest.TestCase):
    def test_legacy_tools_files_removed(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / "src" / "tools" / "base.py").exists())
        self.assertFalse((root / "src" / "tools" / "registry.py").exists())

    def test_no_legacy_tools_registry_references(self) -> None:
        root = Path(__file__).resolve().parents[1]
        checked = [
            root / "src" / "agent" / "core.py",
            root / "src" / "skills" / "loader.py",
            root / "README.md",
        ]

        banned = [
            "from tools.registry import ToolRegistry",
            "ToolRegistry()",
            "from tools.base import Tool",
            "tools.py",
        ]

        for file in checked:
            text = file.read_text(encoding="utf-8")
            for token in banned:
                self.assertNotIn(token, text, f"{token} found in {file}")


if __name__ == "__main__":
    unittest.main()
