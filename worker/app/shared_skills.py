from __future__ import annotations

import os
from pathlib import Path


def get_shared_skills_root() -> Path:
    return Path(os.getenv("MAIN_AGENT_SKILLS_ROOT", "/data/shared/skills/main-agent")).resolve()


def _collect_skill_entries(root: Path) -> list[dict[str, Path]]:
    entries: list[dict[str, Path]] = []

    # Structured skills: <skill-name>/SKILL.md
    for skill_dir in sorted([p for p in root.iterdir() if p.is_dir()]):
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists() and skill_md.is_file():
            entries.append({"id": skill_dir.name, "skill_md": skill_md})

    # Backward-compatible flat skills: *.md
    for file_path in sorted([p for p in root.glob("*.md") if p.is_file()]):
        entries.append({"id": file_path.name, "skill_md": file_path})

    entries.sort(key=lambda item: item["skill_md"].stat().st_mtime, reverse=True)
    return entries


def _extract_skill_summary(skill_md: Path) -> tuple[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Invalid SKILL.md frontmatter in {skill_md}")

    fm_end = None
    for i in range(1, min(len(lines), 120)):
        if lines[i].strip() == "---":
            fm_end = i
            break
    if fm_end is None:
        raise ValueError(f"Invalid SKILL.md frontmatter in {skill_md}")

    title = ""
    description = ""
    for raw in lines[1:fm_end]:
        line = raw.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip().strip("'").strip('"')
        if key == "name" and value:
            title = value
        elif key == "description" and value:
            description = value

    if not title or not description:
        raise ValueError(f"Missing 'name' or 'description' in SKILL.md frontmatter: {skill_md}")
    return title, description[:220]


def search_shared_skills(query: str, limit: int = 10) -> list[dict[str, str]]:
    root = get_shared_skills_root()
    if not root.exists():
        return []

    term = query.strip().lower()
    entries = _collect_skill_entries(root)

    results: list[dict[str, str]] = []
    for entry in entries:
        skill_id = entry["id"]
        path = entry["skill_md"]
        try:
            title, description = _extract_skill_summary(path)
        except ValueError:
            continue
        haystack = f"{skill_id}\n{title}\n{description}".lower()
        if term and term not in haystack:
            continue
        preview = description or title
        results.append(
            {
                "skill_id": skill_id,
                "path": str(path),
                "title": title,
                "preview": preview,
            }
        )
        if len(results) >= limit:
            break

    return results


def read_shared_skill(skill_name: str) -> str:
    root = get_shared_skills_root()
    if not root.exists():
        raise FileNotFoundError("Skills directory not found")

    safe_name = Path(skill_name).name
    structured_path = (root / safe_name / "SKILL.md").resolve()
    if structured_path.exists() and structured_path.is_file() and structured_path.parent.parent == root:
        return structured_path.read_text(encoding="utf-8")

    flat_path = (root / safe_name).resolve()
    if flat_path.exists() and flat_path.is_file() and flat_path.parent == root:
        return flat_path.read_text(encoding="utf-8")

    raise FileNotFoundError("Skill not found. Use <skill-dir>/SKILL.md via its directory name or a legacy .md filename")
