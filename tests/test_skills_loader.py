from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills import loader


class SkillsLoaderTests(unittest.TestCase):
    def test_load_enabled_skills_returns_skill_dirs_not_tool_objects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill_dir = base / "demo_skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                """---
name: demo_skill
description: Demo skill for tests.
---

## When to use
Use for demo only.
""",
                encoding="utf-8",
            )

            original = loader.SKILLS_DIR
            loader.SKILLS_DIR = base
            try:
                summary, skill_dirs = loader.load_enabled_skills(["demo_skill"])
            finally:
                loader.SKILLS_DIR = original

            self.assertIn("demo_skill", summary)
            self.assertEqual(skill_dirs, [skill_dir])
            self.assertTrue(all(isinstance(p, Path) for p in skill_dirs))


if __name__ == "__main__":
    unittest.main()
