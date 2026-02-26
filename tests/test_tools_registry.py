from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent.prompt_builder import build_sys_prompt, SYSTEM_PROMPT


class PromptBuilderTests(unittest.TestCase):
    def test_build_sys_prompt_with_skills_and_tools(self) -> None:
        """Verify build_sys_prompt formats skills and tools correctly."""
        result = build_sys_prompt(
            skills_summary="time_skill: Get current time. Use when asking about time.",
            tool_list_text="time.now: Returns current time | args={}"
        )
        self.assertIn("time_skill", result)
        self.assertIn("time.now", result)
        self.assertIn("SKILLS SUMMARY:", result)
        self.assertIn("AVAILABLE TOOLS:", result)

    def test_build_sys_prompt_with_empty_skills(self) -> None:
        """Verify build_sys_prompt handles empty skills."""
        result = build_sys_prompt(
            skills_summary="",
            tool_list_text="tool1: description | args={}"
        )
        self.assertIn("(no skills enabled)", result)
        self.assertIn("tool1", result)

    def test_build_sys_prompt_with_empty_tools(self) -> None:
        """Verify build_sys_prompt handles empty tools."""
        result = build_sys_prompt(
            skills_summary="skill1: description",
            tool_list_text=""
        )
        self.assertIn("skill1", result)
        self.assertIn("(no tools registered)", result)

    def test_build_sys_prompt_with_both_empty(self) -> None:
        """Verify build_sys_prompt handles both empty."""
        result = build_sys_prompt(skills_summary="", tool_list_text="")
        self.assertIn("(no skills enabled)", result)
        self.assertIn("(no tools registered)", result)

    def test_build_sys_prompt_strips_whitespace(self) -> None:
        """Verify build_sys_prompt strips whitespace from inputs."""
        result = build_sys_prompt(
            skills_summary="  skill1: desc  ",
            tool_list_text="  tool1: desc  "
        )
        self.assertIn("skill1", result)
        self.assertIn("tool1", result)

    def test_system_prompt_contains_rules(self) -> None:
        """Verify SYSTEM_PROMPT contains expected rules."""
        self.assertIn("Only use tools listed below", SYSTEM_PROMPT)
        self.assertIn("Never hallucinate tool names", SYSTEM_PROMPT)
        self.assertIn("SKILLS SUMMARY:", SYSTEM_PROMPT)
        self.assertIn("AVAILABLE TOOLS:", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
