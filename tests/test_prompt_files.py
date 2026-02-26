from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent.prompt_builder import build_sys_prompt
from agent.prompt_files import PROMPT_FILE_NAMES, compose_prompt_context, ensure_prompt_files


class PromptFilesTests(unittest.TestCase):
    def test_ensure_prompt_files_initializes_missing_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "alice"
            created = ensure_prompt_files(workspace)
            self.assertEqual({p.name for p in created}, set(PROMPT_FILE_NAMES))
            for name in PROMPT_FILE_NAMES:
                target = workspace / name
                self.assertTrue(target.exists())
                self.assertTrue(target.read_text(encoding="utf-8").strip())

    def test_compose_prompt_context_reads_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            ensure_prompt_files(workspace)
            for name in PROMPT_FILE_NAMES:
                (workspace / name).write_text(f"{name} content", encoding="utf-8")

            context = compose_prompt_context(workspace)
            self.assertIn("AGENTS.md content", context)
            self.assertIn("SOUL.md content", context)
            self.assertIn("USER.md content", context)
            self.assertIn("MEMORY.md content", context)
            self.assertIn("BOOTSTRAP.md content", context)

    def test_build_sys_prompt_embeds_prompt_file_context(self) -> None:
        rendered = build_sys_prompt(
            prompt_context="AGENTS section\nSOUL section",
            tool_list_text="(managed by toolkit)",
        )
        self.assertIn("AGENTS section", rendered)
        self.assertIn("SOUL section", rendered)
        self.assertIn("AVAILABLE TOOLS", rendered)


if __name__ == "__main__":
    unittest.main()
