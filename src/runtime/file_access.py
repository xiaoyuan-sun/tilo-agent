from __future__ import annotations

from pathlib import Path


def normalize_user_id(user_id: str) -> str:
    candidate = (user_id or "").strip()
    if not candidate:
        raise ValueError("user_id is required.")
    if any(ch in candidate for ch in ("/", "\\", "..")):
        raise ValueError(f"Invalid user_id: {user_id}")
    return candidate


def resolve_user_workspace(workspace_base_dir: Path, user_id: str) -> Path:
    base = workspace_base_dir.resolve()
    safe_user_id = normalize_user_id(user_id)
    workspace_dir = (base / safe_user_id).resolve(strict=False)
    try:
        workspace_dir.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Workspace escapes base dir for user_id={user_id}") from exc
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir

def resolve_project_path(project_root: Path, requested_path: str) -> Path:
    raw = (requested_path or "").strip()
    if not raw:
        raise ValueError("Path is required.")

    root = project_root.resolve()
    candidate = Path(raw)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve(strict=False)

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes project root: {requested_path}") from exc

    return resolved


def ensure_writable(target_path: Path, overwrite: bool) -> None:
    if target_path.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing file without overwrite=true: {target_path}"
        )
