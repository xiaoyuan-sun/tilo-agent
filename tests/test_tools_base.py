from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent.protocol import ToolAction, FinalAction


class ToolActionTests(unittest.TestCase):
    def test_from_dict_creates_action(self) -> None:
        """Verify from_dict creates ToolAction with correct name and args."""
        data = {"name": "time.now", "args": {}}
        action = ToolAction.from_dict(data)
        self.assertEqual(action.name, "time.now")
        self.assertEqual(action.args, {})

    def test_from_dict_with_missing_name_defaults_to_empty(self) -> None:
        """Verify from_dict handles missing name."""
        data = {"args": {"x": 1}}
        action = ToolAction.from_dict(data)
        self.assertEqual(action.name, "")
        self.assertEqual(action.args, {"x": 1})

    def test_from_dict_with_missing_args_defaults_to_empty(self) -> None:
        """Verify from_dict handles missing args."""
        data = {"name": "calc"}
        action = ToolAction.from_dict(data)
        self.assertEqual(action.name, "calc")
        self.assertEqual(action.args, {})

    def test_from_dict_with_nested_args(self) -> None:
        """Verify from_dict preserves nested args structure."""
        data = {
            "name": "search",
            "args": {"query": "test", "options": {"limit": 10, "offset": 0}}
        }
        action = ToolAction.from_dict(data)
        self.assertEqual(action.args["options"]["limit"], 10)

    def test_tool_action_is_frozen(self) -> None:
        """Verify ToolAction is immutable (frozen dataclass)."""
        action = ToolAction(name="test", args={})
        with self.assertRaises(FrozenInstanceError):
            action.name = "changed"


class FinalActionTests(unittest.TestCase):
    def test_from_result_creates_action(self) -> None:
        """Verify from_result creates FinalAction with correct result."""
        action = FinalAction.from_result("task completed")
        self.assertEqual(action.result, "task completed")

    def test_from_result_with_empty_string(self) -> None:
        """Verify from_result handles empty string."""
        action = FinalAction.from_result("")
        self.assertEqual(action.result, "")

    def test_from_result_with_multiline(self) -> None:
        """Verify from_result preserves multiline strings."""
        text = "line1\nline2\nline3"
        action = FinalAction.from_result(text)
        self.assertEqual(action.result, text)

    def test_final_action_is_frozen(self) -> None:
        """Verify FinalAction is immutable (frozen dataclass)."""
        action = FinalAction(result="done")
        with self.assertRaises(FrozenInstanceError):
            action.result = "changed"


# Import for FrozenInstanceError check
from dataclasses import FrozenInstanceError


if __name__ == "__main__":
    unittest.main()
