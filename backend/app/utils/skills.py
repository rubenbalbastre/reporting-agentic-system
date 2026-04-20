from __future__ import annotations

import re
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


def get_main_agent_skills_root() -> Path:
    """Return the published shared-skills root used by backend and worker."""
    return Path(os.getenv("MAIN_AGENT_SKILLS_ROOT", "/data/shared/skills")).resolve()


def get_main_agent_skills_drafts_root() -> Path:
    """Return the draft-skills root used while editing skills before publish."""
    return Path(os.getenv("MAIN_AGENT_SKILLS_DRAFTS_ROOT", "/data/shared/skills_drafts")).resolve()


def ensure_child_dir(root: Path, child_name: str) -> Path:
    """Create one direct child directory under `root` and reject path traversal."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    child_dir = (root / child_name).resolve()
    if child_dir.parent != root:
        raise ValueError("Invalid child directory path")
    child_dir.mkdir(parents=True, exist_ok=True)
    return child_dir


def ensure_draft_skill_md(slug: str) -> Path:
    """Ensure a draft skill directory contains a concrete `SKILL.md` file."""
    draft_dir = ensure_child_dir(get_main_agent_skills_drafts_root(), slug)
    skill_md_path = (draft_dir / "SKILL.md").resolve()
    if skill_md_path.parent != draft_dir:
        raise ValueError("Invalid skill markdown path")
    if not skill_md_path.exists():
        skill_md_path.write_text("", encoding="utf-8")
    return skill_md_path


def slugify(text: str, max_len: int = 50) -> str:
    """Convert free text into a filesystem-safe slug with a stable fallback."""
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not cleaned:
        cleaned = "custom-instruction"
    return cleaned[:max_len].strip("-") or "custom-instruction"


def build_skill_markdown(request_text: str) -> str:
    """Build a minimal fallback `SKILL.md` from a raw user teaching prompt."""
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
    """Add YAML frontmatter when agent-generated markdown omitted it."""
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


def _allocate_unique_skill_dir(root: Path, base_name: str) -> tuple[str, Path]:
    """Allocate a unique skill directory, suffixing with a timestamp on collision."""
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
    return dir_name, skill_dir


def create_skill_from_agent_output(skill_name: str, description: str, skill_markdown: str) -> dict[str, str]:
    """Create a published skill package from structured agent output."""
    root = get_main_agent_skills_root()
    root.mkdir(parents=True, exist_ok=True)

    base_name = slugify(skill_name)
    dir_name, skill_dir = _allocate_unique_skill_dir(root, base_name)

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
    """Create a simple published skill package directly from raw user text."""
    # Backward-compatible fallback for direct creation without LLM-generated structure.
    root = get_main_agent_skills_root()
    root.mkdir(parents=True, exist_ok=True)

    base_name = slugify(request_text)
    dir_name, skill_dir = _allocate_unique_skill_dir(root, base_name)

    content = build_skill_markdown(request_text)
    skill_md_path = skill_dir / "SKILL.md"
    skill_md_path.write_text(content, encoding="utf-8")

    return {
        "filename": dir_name,
        "path": str(skill_dir),
        "skill_md_path": str(skill_md_path),
    }


def _parse_frontmatter_name_description(skill_md_text: str) -> tuple[str, str]:
    """Extract `name` and `description` from a `SKILL.md` frontmatter block."""
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


def read_skill_name_description(skill_md_path: str) -> tuple[str, str]:
    """Read `name` and `description` from an on-disk `SKILL.md` file."""
    path = Path(skill_md_path).resolve()
    if not path.exists() or not path.is_file():
        return "", ""
    text = path.read_text(encoding="utf-8")
    return _parse_frontmatter_name_description(text)


def publish_skill_draft(skill_md_path: str) -> dict[str, str]:
    """Move a validated draft skill package into the published skills root."""
    drafts_root = get_main_agent_skills_drafts_root()
    final_root = get_main_agent_skills_root()
    drafts_root.mkdir(parents=True, exist_ok=True)
    final_root.mkdir(parents=True, exist_ok=True)

    draft_md = Path(skill_md_path).resolve()
    if not draft_md.exists() or not draft_md.is_file() or draft_md.name != "SKILL.md":
        raise ValueError("Draft SKILL.md not found")

    try:
        draft_md.relative_to(drafts_root)
    except ValueError as exc:
        raise ValueError("Draft path is outside drafts root") from exc

    skill_name, description = read_skill_name_description(str(draft_md))
    if not skill_name or not description:
        raise ValueError("SKILL.md must include frontmatter name and description")

    slug = slugify(skill_name)
    target_dir = (final_root / slug).resolve()
    if target_dir.exists():
        raise FileExistsError(f"Skill already exists: {slug}")
    if target_dir.parent != final_root:
        raise ValueError("Invalid publish target")

    draft_dir = draft_md.parent.resolve()
    shutil.move(str(draft_dir), str(target_dir))
    final_md = (target_dir / "SKILL.md").resolve()

    return {
        "name": skill_name,
        "description": description,
        "slug": slug,
        "skill_md_path": str(final_md),
        "path": str(target_dir),
    }


def list_existing_skills(limit: int = 200) -> list[dict[str, str]]:
    """List published skills with lightweight metadata for skill discovery APIs."""
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
