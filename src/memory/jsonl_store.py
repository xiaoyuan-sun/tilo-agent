from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.file_access import normalize_user_id


class JsonlMemoryStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or Path.cwd() / "data").resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str, user_id: str = "default") -> Path:
        safe_user_id = normalize_user_id(user_id)
        if safe_user_id == "default":
            return self.base_dir / f"{session_id}.jsonl"
        return self.base_dir / safe_user_id / f"{session_id}.jsonl"

    def _legacy_path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.jsonl"

    def append(self, session_id: str, record: dict[str, Any], user_id: str = "default") -> None:
        path = self._path(session_id, user_id=user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False))
            fh.write("\n")

    def load(self, session_id: str, user_id: str = "default") -> list[dict[str, Any]]:
        path = self._path(session_id, user_id=user_id)
        if not path.exists():
            safe_user_id = normalize_user_id(user_id)
            if safe_user_id != "default":
                legacy_path = self._legacy_path(session_id)
                if legacy_path.exists():
                    path = legacy_path
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
