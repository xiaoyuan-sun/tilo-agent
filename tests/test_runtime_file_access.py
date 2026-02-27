from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runtime.file_access import ensure_writable, resolve_project_path, resolve_user_workspace


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


class TestResolveUserWorkspace:
    def test_builds_isolated_path_per_user(self, tmp_path: Path) -> None:
        base = tmp_path / "workspaces"
        alice = resolve_user_workspace(base, "alice")
        bob = resolve_user_workspace(base, "bob")
        assert alice == (base / "alice").resolve()
        assert bob == (base / "bob").resolve()
        assert alice != bob
        assert alice.exists()
        assert bob.exists()
