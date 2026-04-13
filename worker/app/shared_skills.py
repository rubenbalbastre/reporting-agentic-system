from __future__ import annotations

import os
from pathlib import Path


def get_shared_skills_root() -> Path:
    return Path(os.getenv("MAIN_AGENT_SKILLS_ROOT", "/data/shared/skills/main-agent")).resolve()


def search_shared_skills(query: str, limit: int = 10) -> list[dict[str, str]]:
    root = get_shared_skills_root()
    if not root.exists():
        return []

    term = query.strip().lower()
    files = sorted(
        [p for p in root.glob("*.md") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    results: list[dict[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        haystack = f"{path.name}\n{text}".lower()
        if term and term not in haystack:
            continue
        preview = " ".join(text.split())[:220]
        results.append({"filename": path.name, "path": str(path), "preview": preview})
        if len(results) >= limit:
            break

    return results


def read_shared_skill(filename: str) -> str:
    root = get_shared_skills_root()
    if not root.exists():
        raise FileNotFoundError("Skills directory not found")

    safe_name = Path(filename).name
    path = (root / safe_name).resolve()
    if path.parent != root or not path.exists() or not path.is_file():
        raise FileNotFoundError("Skill file not found")

    return path.read_text(encoding="utf-8")
