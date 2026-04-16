from fastapi import APIRouter, HTTPException

from app.schemas import (
    CreateMessageRequest,
    CreateSkillRequest,
    PublishSkillRequest,
    Skill,
    SkillConversation,
    SkillMessage,
    SkillSummary,
    TeachAgentRequest,
    TeachAgentResponse,
)
from app.services.skill_service import (
    generate_published_skill,
    run_skill_conversation_turn,
    teach_and_create_skill,
)
from app.utils.db import get_db_connection
from app.utils.skill_utils import (
    create_skill_row,
    delete_skill_filesystem,
    get_skill,
    get_skill_conversation,
    list_skill_folder_files,
    open_published_skill_in_draft,
    read_skill_markdown,
)
from app.utils.skills import list_existing_skills

router = APIRouter()


@router.post("/agent/teach", response_model=TeachAgentResponse, status_code=201)
async def teach_agent(payload: TeachAgentRequest) -> TeachAgentResponse:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Teaching message content is required")

    result = await teach_and_create_skill(content)
    return TeachAgentResponse(**result)


@router.get("/skills", response_model=list[Skill])
def list_skills() -> list[Skill]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, slug, skill_md_path, created_at, updated_at
                FROM skills
                ORDER BY id DESC;
                """
            )
            rows = cur.fetchall()
    return [Skill(**row) for row in rows]


@router.get("/skills/{skill_id}/markdown")
def get_skill_markdown(skill_id: int) -> dict[str, str]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            skill = get_skill(cur, skill_id)
    return {"content": read_skill_markdown(skill)}


@router.get("/skills/{skill_id}/files")
def get_skill_files(skill_id: int) -> dict[str, list[str]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            skill = get_skill(cur, skill_id)
    return {"files": list_skill_folder_files(skill)}


@router.post("/skills", response_model=Skill, status_code=201)
def create_skill(payload: CreateSkillRequest) -> Skill:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Skill name is required")
    row = create_skill_row(name=name, description="")
    return Skill(**row)


@router.post("/skills/{skill_id}/open-draft", response_model=Skill, status_code=201)
def open_skill_in_draft(skill_id: int) -> Skill:
    row = open_published_skill_in_draft(skill_id)
    return Skill(**row)


@router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: int) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            skill = get_skill(cur, skill_id)
            cur.execute("DELETE FROM skills WHERE id = %s;", (skill_id,))
        conn.commit()
    delete_skill_filesystem(skill)


@router.get("/skills/{skill_id}/conversations", response_model=list[SkillConversation])
def list_skill_conversations(skill_id: int) -> list[SkillConversation]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            get_skill(cur, skill_id)
            cur.execute(
                """
                SELECT id, skill_id, created_at
                FROM skill_conversations
                WHERE skill_id = %s
                ORDER BY id DESC;
                """,
                (skill_id,),
            )
            rows = cur.fetchall()
    return [SkillConversation(**row) for row in rows]


@router.post("/skills/{skill_id}/conversations", response_model=SkillConversation, status_code=201)
def create_skill_conversation(skill_id: int) -> SkillConversation:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            get_skill(cur, skill_id)
            cur.execute(
                """
                INSERT INTO skill_conversations (skill_id)
                VALUES (%s)
                RETURNING id, skill_id, created_at;
                """,
                (skill_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return SkillConversation(**row)


@router.get("/skill-conversations/{skill_conversation_id}/messages", response_model=list[SkillMessage])
def list_skill_conversation_messages(skill_conversation_id: int) -> list[SkillMessage]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            convo = get_skill_conversation(cur, skill_conversation_id)
            cur.execute(
                """
                SELECT id, %s AS skill_id, skill_conversation_id, role, content, created_at
                FROM skill_messages
                WHERE skill_conversation_id = %s
                ORDER BY id ASC;
                """,
                (convo["skill_id"], skill_conversation_id),
            )
            rows = cur.fetchall()
    return [SkillMessage(**row) for row in rows]


@router.post("/skill-conversations/{skill_conversation_id}/messages", status_code=201)
async def create_skill_conversation_message(skill_conversation_id: int, payload: CreateMessageRequest):
    user_content = payload.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content is required")

    return await run_skill_conversation_turn(
        skill_conversation_id=skill_conversation_id,
        user_content=user_content,
    )


@router.post("/skills/{skill_id}/publish", response_model=Skill, status_code=200)
async def publish_skill(skill_id: int, payload: PublishSkillRequest) -> Skill:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            skill = get_skill(cur, skill_id)
            skill_conversation_id = payload.skill_conversation_id
            if skill_conversation_id is None:
                cur.execute(
                    """
                    SELECT id, skill_id, created_at
                    FROM skill_conversations
                    WHERE skill_id = %s
                    ORDER BY id DESC
                    LIMIT 1;
                    """,
                    (skill_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=400, detail="No skill conversation found to publish")
                skill_conversation_id = row["id"]
            convo = get_skill_conversation(cur, skill_conversation_id)
            if convo["skill_id"] != skill_id:
                raise HTTPException(status_code=400, detail="Conversation does not belong to skill")

            cur.execute(
                """
                SELECT role, content
                FROM skill_messages
                WHERE skill_conversation_id = %s
                ORDER BY id ASC;
                """,
                (skill_conversation_id,),
            )
            messages = cur.fetchall()

    _, update_fields = await generate_published_skill(skill, messages)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE skills
                SET name = %s,
                    description = %s,
                    slug = %s,
                    skill_md_path = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, name, description, slug, skill_md_path, created_at, updated_at;
                """,
                (
                    update_fields["name"],
                    update_fields["description"],
                    update_fields["slug"],
                    update_fields["skill_md_path"],
                    skill_id,
                ),
            )
            updated = cur.fetchone()
        conn.commit()
    return Skill(**updated)


@router.get("/agent/skills", response_model=list[SkillSummary])
def list_agent_skills() -> list[SkillSummary]:
    return [SkillSummary(**item) for item in list_existing_skills()]
