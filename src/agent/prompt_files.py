from __future__ import annotations

from pathlib import Path

PROMPT_FILE_NAMES = (
    "AGENTS.md",
    "SOUL.md",
    "USER.md",
    "MEMORY.md",
    "BOOTSTRAP.md",
)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def ensure_prompt_files(workspace_dir: Path) -> list[Path]:
    workspace = workspace_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for name in PROMPT_FILE_NAMES:
        target = workspace / name
        if target.exists():
            continue
        template = (_PROMPTS_DIR / name).read_text(encoding="utf-8")
        target.write_text(template, encoding="utf-8")
        created.append(target)
    return created


def compose_prompt_context(workspace_dir: Path) -> str:
    workspace = workspace_dir.resolve()
    ensure_prompt_files(workspace)
    sections: list[str] = []
    for name in PROMPT_FILE_NAMES:
        body = (workspace / name).read_text(encoding="utf-8").strip()
        sections.append(f"### {name}\n{body}")
    return "\n\n".join(sections)
