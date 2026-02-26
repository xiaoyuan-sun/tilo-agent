from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from runtime.file_access import resolve_user_workspace


def new_session_id() -> str:
    return uuid4().hex


@dataclass
class SessionContext:
    session_id: str
    enabled_skills: list[str] | None = None
    user_id: str = "default"
    timezone: str = "Asia/Seoul"
    memory_dir: Path = Path("./data")
    workspace_base_dir: Path = Path("./workspaces")
    max_iters: int = 6
    project_root: Path = Path.cwd().resolve()

    def workspace_dir(self) -> Path:
        return resolve_user_workspace(self.workspace_base_dir, self.user_id)
