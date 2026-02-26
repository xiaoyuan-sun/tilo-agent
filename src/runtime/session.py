from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


def new_session_id() -> str:
    return uuid4().hex


@dataclass
class SessionContext:
    session_id: str
    enabled_skills: list[str]
    timezone: str = "Asia/Seoul"
    memory_dir: Path = Path("./data")
    max_iters: int = 6
    project_root: Path = Path.cwd().resolve()
