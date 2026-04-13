from __future__ import annotations

import re
import os
from datetime import datetime, timezone
from pathlib import Path


SKILL_FILE_PREFIX = "skill_"


def get_main_agent_skills_root() -> Path:
    return Path(os.getenv("MAIN_AGENT_SKILLS_ROOT", "/data/shared/skills/main-agent")).resolve()


def slugify(text: str, max_len: int = 50) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not cleaned:
        cleaned = "custom-instruction"
    return cleaned[:max_len].strip("-") or "custom-instruction"


def build_skill_markdown(request_text: str) -> str:
    request = request_text.strip()
    return (
        "# Skill: Main Agent User Instruction\n\n"
        "## Purpose\n"
        "Capture a user-provided behavior instruction for the main reporting agent.\n\n"
        "## User Request\n"
        f"{request}\n\n"
        "## Agent Behavior\n"
        "When relevant to the current user task, prioritize and apply the instruction above "
        "while preserving accuracy, safety, and consistency with system constraints.\n"
    )


def create_skill_from_request(request_text: str) -> dict[str, str]:
    root = get_main_agent_skills_root()
    root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = slugify(request_text)
    filename = f"{SKILL_FILE_PREFIX}{timestamp}_{slug}.md"

    skill_path = (root / filename).resolve()
    if skill_path.parent != root:
        raise ValueError("Invalid skill path")

    content = build_skill_markdown(request_text)
    skill_path.write_text(content, encoding="utf-8")

    return {
        "filename": filename,
        "path": str(skill_path),
        "content": content,
    }


def load_main_agent_skills(limit: int = 20) -> list[str]:
    root = get_main_agent_skills_root()
    if not root.exists():
        return []

    skill_files = sorted(
        [p for p in root.glob("*.md") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    loaded: list[str] = []
    for path in skill_files[:limit]:
        text = path.read_text(encoding="utf-8").strip()
        if text:
            loaded.append(text)

    return loaded
