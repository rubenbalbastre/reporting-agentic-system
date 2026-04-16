import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from fastapi import HTTPException

from app.utils.db import get_db_connection
from app.schemas import SkillMessage
from app.utils.chat_input import build_chat_input
from app.utils.skills import slugify


def get_skill(cur: Any, skill_id: int) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, name, description, slug, skill_md_path, created_at, updated_at
        FROM skills
        WHERE id = %s;
        """,
        (skill_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return row


def get_skill_conversation(cur: Any, skill_conversation_id: int) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, skill_id, created_at
        FROM skill_conversations
        WHERE id = %s;
        """,
        (skill_conversation_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Skill conversation not found")
    return row


def read_skill_markdown(skill: dict[str, Any]) -> str:
    raw_path = (skill.get("skill_md_path") or "").strip()
    if not raw_path:
        raise HTTPException(status_code=404, detail="Skill markdown has not been published yet")

    path = Path(raw_path).resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Skill markdown file not found")
    return path.read_text(encoding="utf-8")


def parse_skill_agent_output(raw_output: str) -> dict[str, str]:
    text = (raw_output or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    payload = json.loads(text)
    return {
        "skill_name": str(payload.get("skill_name", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "skill_markdown": str(payload.get("skill_markdown", "")).strip(),
    }


def build_skill_chat_input(
    history_rows: list[dict[str, Any]], user_content: str, max_messages: int = 20
) -> list[dict[str, str]]:
    return build_chat_input(
        "Skill teaching conversation:",
        history_rows,
        user_content,
        max_messages=max_messages,
    )


def load_skill_conversation_history(skill_conversation_id: int) -> tuple[int, list[dict[str, Any]]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            convo = get_skill_conversation(cur, skill_conversation_id)
            cur.execute(
                """
                SELECT role, content
                FROM skill_messages
                WHERE skill_conversation_id = %s
                ORDER BY id ASC;
                """,
                (skill_conversation_id,),
            )
            return convo["skill_id"], cur.fetchall()


def _insert_skill_message(
    cur: Any, skill_conversation_id: int, skill_id: int, role: str, content: str
) -> dict[str, Any]:
    cur.execute(
        """
        INSERT INTO skill_messages (skill_conversation_id, role, content)
        VALUES (%s, %s, %s)
        RETURNING id, %s AS skill_id, %s AS skill_conversation_id, role, content, created_at;
        """,
        (skill_conversation_id, role, content, skill_id, skill_conversation_id),
    )
    return cur.fetchone()


def persist_skill_message_pair(
    skill_conversation_id: int, skill_id: int, user_content: str, assistant_content: str
) -> tuple[SkillMessage, SkillMessage]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            get_skill(cur, skill_id)
            get_skill_conversation(cur, skill_conversation_id)
            user_row = _insert_skill_message(cur, skill_conversation_id, skill_id, "user", user_content)
            assistant_row = _insert_skill_message(cur, skill_conversation_id, skill_id, "assistant", assistant_content)
        conn.commit()
    return SkillMessage(**user_row), SkillMessage(**assistant_row)


def create_skill_row(name: str, description: str = "") -> dict[str, Any]:
    base_slug = slugify(name)
    slug = base_slug

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            row = None
            for attempt in range(2):
                try:
                    cur.execute(
                        """
                        INSERT INTO skills (name, description, slug)
                        VALUES (%s, %s, %s)
                        RETURNING id, name, description, slug, skill_md_path, created_at, updated_at;
                        """,
                        (name, description, slug),
                    )
                    row = cur.fetchone()
                    break
                except psycopg2.Error:
                    conn.rollback()
                    if attempt == 1:
                        raise
                    suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                    slug = f"{base_slug}-{suffix}"
            if row is None:
                raise HTTPException(status_code=500, detail="Failed to create skill")
            cur.execute(
                """
                INSERT INTO skill_conversations (skill_id)
                VALUES (%s);
                """,
                (row["id"],),
            )
        conn.commit()
    return row


def delete_skill_filesystem(skill: dict[str, Any]) -> None:
    raw_path = (skill.get("skill_md_path") or "").strip()
    if not raw_path:
        return

    try:
        skill_md = Path(raw_path).resolve()
        if skill_md.exists() and skill_md.is_file():
            skill_md.unlink()
        skill_dir = skill_md.parent
        if skill_dir.exists() and skill_dir.is_dir():
            shutil.rmtree(skill_dir, ignore_errors=True)
    except Exception:
        pass
