# Pytest Core Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add pytest-based unit tests for core business logic modules (JsonlMemoryStore, MockModel, skills/loader) with happy path and edge case coverage.

**Architecture:** Migrate existing unittest tests to pytest, delete obsolete migration test, add comprehensive tests for untested core modules using pytest fixtures and tmp_path.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio

---

## Prerequisites

**Add pytest dependencies to pyproject.toml:**

```toml
[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio"]
```

---

### Task 1: Add pytest Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dev dependencies**

Add to `pyproject.toml` after the `dependencies` section:

```toml
[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
```

**Step 2: Install dependencies**

Run: `conda run -n tilo-agent pip install -e ".[dev]"`
Expected: pytest and pytest-asyncio installed

**Step 3: Verify pytest works**

Run: `conda run -n tilo-agent pytest --version`
Expected: pytest version displayed

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pytest and pytest-asyncio dev dependencies

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Delete Obsolete Test

**Files:**
- Delete: `tests/test_no_legacy_tools_refs.py`

**Step 1: Delete the obsolete test file**

Run: `rm tests/test_no_legacy_tools_refs.py`

**Step 2: Verify remaining tests still pass**

Run: `conda run -n tilo-agent python -m unittest discover tests/ -v`
Expected: 2 tests pass (skills_loader, runtime_file_access)

**Step 3: Commit**

```bash
git add tests/
git commit -m "test: remove obsolete legacy tools migration test

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Migrate test_runtime_file_access to pytest

**Files:**
- Modify: `tests/test_runtime_file_access.py`

**Step 1: Rewrite with pytest style**

Replace entire file content with:

```python
from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runtime.file_access import ensure_writable, resolve_project_path


class TestResolveProjectPath:
    def test_allows_relative_file_inside_root(self, tmp_path: Path) -> None:
        resolved = resolve_project_path(tmp_path, "notes/todo.txt")
        assert resolved == (tmp_path / "notes" / "todo.txt").resolve()

    def test_rejects_escape_with_dotdot(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="escapes project root"):
            resolve_project_path(tmp_path, "../outside.txt")

    def test_rejects_empty_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path is required"):
            resolve_project_path(tmp_path, "")

    def test_allows_absolute_path_inside_root(self, tmp_path: Path) -> None:
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        resolved = resolve_project_path(tmp_path, str(subdir))
        assert resolved == subdir.resolve()


class TestEnsureWritable:
    def test_rejects_existing_without_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "a.txt"
        target.write_text("x", encoding="utf-8")
        with pytest.raises(FileExistsError, match="Refusing to overwrite"):
            ensure_writable(target, overwrite=False)

    def test_allows_existing_with_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "a.txt"
        target.write_text("x", encoding="utf-8")
        # Should not raise
        ensure_writable(target, overwrite=True)

    def test_allows_nonexistent_file(self, tmp_path: Path) -> None:
        target = tmp_path / "new.txt"
        # Should not raise
        ensure_writable(target, overwrite=False)
```

**Step 2: Run tests to verify migration**

Run: `conda run -n tilo-agent pytest tests/test_runtime_file_access.py -v`
Expected: 7 tests pass

**Step 3: Commit**

```bash
git add tests/test_runtime_file_access.py
git commit -m "test: migrate test_runtime_file_access to pytest

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Migrate test_skills_loader to pytest

**Files:**
- Modify: `tests/test_skills_loader.py`

**Step 1: Rewrite with pytest style**

Replace entire file content with:

```python
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
```

**Step 2: Run tests to verify migration**

Run: `conda run -n tilo-agent pytest tests/test_skills_loader.py -v`
Expected: 13 tests pass

**Step 3: Commit**

```bash
git add tests/test_skills_loader.py
git commit -m "test: migrate test_skills_loader to pytest with expanded coverage

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Create test_jsonl_store.py

**Files:**
- Create: `tests/test_jsonl_store.py`

**Step 1: Write the test file**

```python
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
```

**Step 2: Run tests to verify**

Run: `conda run -n tilo-agent pytest tests/test_jsonl_store.py -v`
Expected: 9 tests pass

**Step 3: Commit**

```bash
git add tests/test_jsonl_store.py
git commit -m "test: add comprehensive tests for JsonlMemoryStore

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Create test_mock_model.py

**Files:**
- Create: `tests/test_mock_model.py`

**Step 1: Write the test file**

```python
from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from llm.client import MockModel


@pytest.fixture
def model():
    return MockModel()


class TestMockModelTimeIntent:
    @pytest.mark.asyncio
    async def test_returns_time_tool_for_chinese_time_query(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "现在几点"}]}]
        response = await model(prompt)
        assert response.content[0]["type"] == "tool_use"
        assert response.content[0]["name"] == "time.now"

    @pytest.mark.asyncio
    async def test_returns_time_tool_for_english_keywords(self, model: MockModel) -> None:
        keywords = ["what time", "current time", "date today", "now"]
        for kw in keywords:
            prompt = [{"role": "user", "content": [{"text": kw}]}]
            response = await model(prompt)
            assert response.content[0]["name"] == "time.now", f"failed for: {kw}"


class TestMockModelMathIntent:
    @pytest.mark.asyncio
    async def test_returns_math_tool_for_simple_expression(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "计算 3 + 5"}]}]
        response = await model(prompt)
        assert response.content[0]["type"] == "tool_use"
        assert response.content[0]["name"] == "math.calc"
        assert response.content[0]["input"]["expression"] == "3 + 5"

    @pytest.mark.asyncio
    async def test_extracts_expression_with_spaces(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "计算 (10 + 2) * 3"}]}]
        response = await model(prompt)
        assert response.content[0]["name"] == "math.calc"
        assert "(10 + 2) * 3" in response.content[0]["input"]["expression"]

    @pytest.mark.asyncio
    async def test_handles_division_and_subtraction(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "100 / 5 - 10"}]}]
        response = await model(prompt)
        assert response.content[0]["name"] == "math.calc"


class TestMockModelFallback:
    @pytest.mark.asyncio
    async def test_returns_text_for_unknown_intent(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": [{"text": "讲个笑话"}]}]
        response = await model(prompt)
        assert response.content[0]["type"] == "text"
        assert "模拟回答" in response.content[0]["text"]

    @pytest.mark.asyncio
    async def test_handles_empty_prompt(self, model: MockModel) -> None:
        prompt = []
        response = await model(prompt)
        assert response.content[0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_handles_empty_user_text(self, model: MockModel) -> None:
        prompt = [{"role": "user", "content": []}]
        response = await model(prompt)
        assert response.content[0]["type"] == "text"


class TestMockModelPromptExtraction:
    @pytest.mark.asyncio
    async def test_extracts_latest_user_text(self, model: MockModel) -> None:
        prompt = [
            {"role": "user", "content": [{"text": "first message"}]},
            {"role": "assistant", "content": [{"text": "response"}]},
            {"role": "user", "content": [{"text": "现在几点"}]},
        ]
        response = await model(prompt)
        # Should use the last user message for intent detection
        assert response.content[0]["name"] == "time.now"

    @pytest.mark.asyncio
    async def test_ignores_assistant_messages(self, model: MockModel) -> None:
        prompt = [
            {"role": "assistant", "content": [{"text": "what time is it"}]},
            {"role": "user", "content": [{"text": "hello"}]},
        ]
        response = await model(prompt)
        # "hello" has no time/math intent, so fallback
        assert response.content[0]["type"] == "text"


class TestMockModelPriority:
    @pytest.mark.asyncio
    async def test_time_takes_priority_over_math(self, model: MockModel) -> None:
        # When both intents match, time should win
        prompt = [{"role": "user", "content": [{"text": "时间 3 + 5"}]}]
        response = await model(prompt)
        assert response.content[0]["name"] == "time.now"
```

**Step 2: Create pytest.ini for async mode**

Create `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_paths = src
```

**Step 3: Run tests to verify**

Run: `conda run -n tilo-agent pytest tests/test_mock_model.py -v`
Expected: 12 tests pass

**Step 4: Commit**

```bash
git add tests/test_mock_model.py pytest.ini
git commit -m "test: add comprehensive async tests for MockModel

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Final Verification

**Step 1: Run all tests**

Run: `conda run -n tilo-agent pytest tests/ -v`
Expected: All tests pass (41 tests total)

**Step 2: Run with coverage (optional)**

Run: `conda run -n tilo-agent pip install pytest-cov && conda run -n tilo-agent pytest tests/ --cov=src --cov-report=term-missing`

**Step 3: Final commit (if any changes)**

```bash
git status
# If clean, no action needed
```

---

## Summary

| Task | Action | Tests Added |
|------|--------|-------------|
| 1 | Add pytest deps | 0 |
| 2 | Delete obsolete test | -2 |
| 3 | Migrate file_access | 7 |
| 4 | Migrate + expand skills_loader | 13 |
| 5 | Create jsonl_store tests | 9 |
| 6 | Create mock_model tests | 12 |
| 7 | Final verification | - |

**Total: ~39 tests** (up from 3)
