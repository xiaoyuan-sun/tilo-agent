from __future__ import annotations

from pathlib import Path


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
