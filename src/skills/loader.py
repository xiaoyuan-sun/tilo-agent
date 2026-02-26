from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

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
    if doc.startswith("---"):
        lines = doc.splitlines()
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                frontmatter = lines[1:idx]
                name = ""
                description = ""
                for line in frontmatter:
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                        continue
                    if line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
                        continue
                return name or "(unknown)", description or "(no description)"

    # fallback for non-frontmatter markdown
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


def load_enabled_skills(enabled: Iterable[str]) -> Tuple[str, List[Path]]:
    enabled = list(enabled)
    summaries: List[str] = []
    skill_dirs: List[Path] = []
    for skill_name in enabled:
        skill_dir = SKILLS_DIR / skill_name
        if not skill_dir.exists():
            continue
        doc = _read_skill_doc(skill_dir / "SKILL.md")
        name, description = _parse_meta(doc)
        when_section = _extract_section(doc, "When to use")
        when_to_use = when_section.splitlines()[0] if when_section else ""
        separator = " " if description.endswith((".", "!", "?", "。", "！", "？")) else ". "
        summary = f"{name}: {description}{separator}{when_to_use}".strip()
        summaries.append(summary)
        skill_dirs.append(skill_dir)
    return "\n".join(summaries), skill_dirs
