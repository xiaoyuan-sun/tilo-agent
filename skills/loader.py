from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Iterable, List, Tuple

from tools.base import Tool

SKILLS_DIR = Path(__file__).resolve().parent / "builtin"


def scan_builtin_skills() -> List[str]:
    if not SKILLS_DIR.exists():
        return []
    return sorted(
        p.name for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    )


def _read_skill_doc(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_meta(doc: str) -> Tuple[str, str]:
    name = ""
    description = ""
    for line in doc.splitlines():
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            continue
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip()
            continue
        if name and description:
            break
    return name or "(unknown)", description or "(no description)"


def _extract_section(doc: str, title: str) -> str:
    marker = f"## {title}"
    start = doc.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    rest = doc[start:]
    end = rest.find("## ")
    section = rest if end == -1 else rest[:end]
    return section.strip()


def _import_skill_tools(skill_dir: Path) -> List[Tool]:
    tools_file = skill_dir / "tools.py"
    if not tools_file.exists():
        return []
    spec = importlib.util.spec_from_file_location(f"skills.builtin.{skill_dir.name}.tools", tools_file)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return [tool for tool in getattr(module, "TOOLS", []) if isinstance(tool, Tool)]


def load_enabled_skills(enabled: Iterable[str]) -> Tuple[str, List[Tool]]:
    enabled = list(enabled)
    summaries: List[str] = []
    all_tools: List[Tool] = []
    for skill_name in enabled:
        skill_dir = SKILLS_DIR / skill_name
        if not skill_dir.exists():
            continue
        doc = _read_skill_doc(skill_dir / "SKILL.md")
        name, description = _parse_meta(doc)
        when_section = _extract_section(doc, "When to use")
        when_to_use = when_section.splitlines()[0] if when_section else ""
        summary = f"{name}: {description}. {when_to_use}".strip()
        summaries.append(summary)
        all_tools.extend(_import_skill_tools(skill_dir))
        # future hooks: filter based on skill config, progressive disclosure, etc.
    return "\n".join(summaries), all_tools
