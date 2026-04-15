from __future__ import annotations

import re
import os
from datetime import datetime, timezone
from pathlib import Path


def get_main_agent_skills_root() -> Path:
    return Path(os.getenv("MAIN_AGENT_SKILLS_ROOT", "/data/shared/skills")).resolve()


def slugify(text: str, max_len: int = 50) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not cleaned:
        cleaned = "custom-instruction"
    return cleaned[:max_len].strip("-") or "custom-instruction"


def build_skill_markdown(request_text: str) -> str:
    request = request_text.strip()
    return (
        "---\n"
        "name: custom-instruction\n"
        "description: User-taught behavior for reporting tasks.\n"
        "---\n\n"
        "# Custom Instruction\n\n"
        "## When to use this skill\n"
        "Use when the user request matches this custom behavior.\n\n"
        "## Instructions\n"
        f"{request}\n"
    )


def _ensure_frontmatter(skill_markdown: str, skill_name: str, description: str) -> str:
    text = skill_markdown.strip()
    if text.startswith("---"):
        return text + "\n"

    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {description}\n"
        "---\n\n"
        f"{text}\n"
    )


def create_skill_from_agent_output(skill_name: str, description: str, skill_markdown: str) -> dict[str, str]:
    root = get_main_agent_skills_root()
    root.mkdir(parents=True, exist_ok=True)

    base_name = slugify(skill_name)
    dir_name = base_name

    skill_dir = (root / dir_name).resolve()
    if skill_dir.parent != root:
        raise ValueError("Invalid skill directory")
    if skill_dir.exists():
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dir_name = f"{base_name}-{suffix}"
        skill_dir = (root / dir_name).resolve()
        if skill_dir.parent != root:
            raise ValueError("Invalid skill directory")
    skill_dir.mkdir(parents=True, exist_ok=False)

    safe_name = slugify(skill_name) or "custom-instruction"
    safe_description = description.strip() or "User-taught behavior for reporting tasks."
    final_markdown = _ensure_frontmatter(skill_markdown, safe_name, safe_description)

    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(final_markdown, encoding="utf-8")

    return {
        "filename": dir_name,
        "path": str(skill_dir),
        "skill_md_path": str(skill_md_path),
    }


def create_skill_from_request(request_text: str) -> dict[str, str]:
    # Backward-compatible fallback for direct creation without LLM-generated structure.
    root = get_main_agent_skills_root()
    root.mkdir(parents=True, exist_ok=True)

    base_name = slugify(request_text)
    dir_name = base_name

    skill_dir = (root / dir_name).resolve()
    if skill_dir.parent != root:
        raise ValueError("Invalid skill directory")
    if skill_dir.exists():
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dir_name = f"{base_name}-{suffix}"
        skill_dir = (root / dir_name).resolve()
        if skill_dir.parent != root:
            raise ValueError("Invalid skill directory")
    skill_dir.mkdir(parents=True, exist_ok=False)

    content = build_skill_markdown(request_text)
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(content, encoding="utf-8")

    return {
        "filename": dir_name,
        "path": str(skill_dir),
        "skill_md_path": str(skill_md_path),
    }


def _parse_frontmatter_name_description(skill_md_text: str) -> tuple[str, str]:
    lines = skill_md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", ""

    end_idx = None
    for i in range(1, min(len(lines), 120)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return "", ""

    name = ""
    description = ""
    for raw in lines[1:end_idx]:
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("'").strip('"')
        if key == "name" and value:
            name = value
        elif key == "description" and value:
            description = value
    return name, description


def list_existing_skills(limit: int = 200) -> list[dict[str, str]]:
    root = get_main_agent_skills_root()
    if not root.exists():
        return []

    entries: list[dict[str, str]] = []
    skill_dirs = sorted(
        [p for p in root.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for skill_dir in skill_dirs[:limit]:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists() or not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        name, description = _parse_frontmatter_name_description(text)
        entries.append(
            {
                "skill_id": skill_dir.name,
                "name": name or skill_dir.name,
                "description": description or "",
                "skill_md_path": str(skill_md),
            }
        )
    return entries
