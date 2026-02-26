from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills import loader


@pytest.fixture
def mock_skills_dir(tmp_path: Path):
    """Create a mock skills directory with a test skill."""
    skill_dir = tmp_path / "demo_skill"
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
    return tmp_path


class TestScanBuiltinSkills:
    def test_returns_dirs_with_skill_md(self, monkeypatch, mock_skills_dir: Path) -> None:
        monkeypatch.setattr(loader, "SKILLS_DIR", mock_skills_dir)
        result = loader.scan_builtin_skills()
        assert result == ["demo_skill"]

    def test_returns_empty_if_no_skills_dir(self, monkeypatch, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(loader, "SKILLS_DIR", nonexistent)
        result = loader.scan_builtin_skills()
        assert result == []

    def test_ignores_dirs_without_skill_md(self, monkeypatch, tmp_path: Path) -> None:
        skill_dir = tmp_path / "incomplete_skill"
        skill_dir.mkdir(parents=True)
        # No SKILL.md file
        monkeypatch.setattr(loader, "SKILLS_DIR", tmp_path)
        result = loader.scan_builtin_skills()
        assert result == []


class TestParseMeta:
    def test_extracts_name_and_description_from_frontmatter(self) -> None:
        doc = """---
name: my_skill
description: A test skill.
---
# My Skill
"""
        name, desc = loader._parse_meta(doc)
        assert name == "my_skill"
        assert desc == "A test skill."

    def test_fallback_without_frontmatter(self) -> None:
        doc = """name: plain_skill
description: Plain description.
Some content here."""
        name, desc = loader._parse_meta(doc)
        assert name == "plain_skill"
        assert desc == "Plain description."

    def test_returns_unknown_for_missing_name(self) -> None:
        doc = """---
description: No name here.
---"""
        name, desc = loader._parse_meta(doc)
        assert name == "(unknown)"
        assert desc == "No name here."

    def test_returns_no_description_for_missing_desc(self) -> None:
        doc = """---
name: only_name
---"""
        name, desc = loader._parse_meta(doc)
        assert name == "only_name"
        assert desc == "(no description)"


class TestExtractSection:
    def test_returns_section_content(self) -> None:
        doc = """# Skill
## When to use
Use this when X happens.
## Other section
More content."""
        result = loader._extract_section(doc, "When to use")
        assert "Use this when X happens." in result

    def test_returns_empty_if_section_missing(self) -> None:
        doc = """# Skill
No sections here."""
        result = loader._extract_section(doc, "When to use")
        assert result == ""

    def test_extracts_only_first_section(self) -> None:
        doc = """## When to use
First line.
## Another section
Should not appear."""
        result = loader._extract_section(doc, "When to use")
        assert "First line." in result
        assert "Should not appear" not in result


class TestLoadEnabledSkills:
    def test_returns_skill_dirs_as_paths(self, monkeypatch, mock_skills_dir: Path) -> None:
        monkeypatch.setattr(loader, "SKILLS_DIR", mock_skills_dir)
        summary, skill_dirs = loader.load_enabled_skills(["demo_skill"])
        assert skill_dirs == [mock_skills_dir / "demo_skill"]
        assert all(isinstance(p, Path) for p in skill_dirs)

    def test_skips_missing_skills(self, monkeypatch, mock_skills_dir: Path) -> None:
        monkeypatch.setattr(loader, "SKILLS_DIR", mock_skills_dir)
        summary, skill_dirs = loader.load_enabled_skills(["demo_skill", "nonexistent"])
        assert len(skill_dirs) == 1
        assert skill_dirs[0].name == "demo_skill"

    def test_summary_includes_skill_info(self, monkeypatch, mock_skills_dir: Path) -> None:
        monkeypatch.setattr(loader, "SKILLS_DIR", mock_skills_dir)
        summary, _ = loader.load_enabled_skills(["demo_skill"])
        assert "demo_skill" in summary
        assert "Demo skill for tests." in summary
