import os
import mimetypes
import re
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from agents import Runner
from pathlib import Path
from app.schemas import (
    Report,
    Conversation,
    Message,
    CreateReportRequest,
    UpdateReportTitleRequest,
    CreateMessageRequest,
    TeachAgentRequest,
    TeachAgentResponse,
    SkillSummary,
    Skill,
    CreateSkillRequest,
    SkillConversation,
    SkillMessage,
    PublishSkillRequest,
)
from app.agents.main_agent import build_main_agent
from app.agents.skill_agent import build_skill_agent, build_skill_chat_agent
from app.utils.skills import create_skill_from_request, create_skill_from_agent_output, list_existing_skills, slugify
from app.utils.workspace_paths import get_report_workspace, resolve_workspace_relative_path
from app.utils.db import get_db_connection
from app.utils.report_utils import (
    build_agent_input,
    delete_report_workspace,
    ensure_report_exists,
    ensure_report_markdown_exists,
    get_conversation,
    load_conversation_history,
    persist_message_pair_for_conversation,
    read_report_markdown,
    render_report_pdf_bytes,
    write_report_markdown,
)
from app.utils.skill_utils import (
    build_skill_chat_input,
    create_skill_row,
    delete_skill_filesystem,
    get_skill,
    get_skill_conversation,
    load_skill_conversation_history,
    parse_skill_agent_output,
    persist_skill_message_pair,
    read_skill_markdown,
)
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client
from contextlib import asynccontextmanager


def _log_langfuse_readiness() -> None:
    langfuse = get_client()
    try:
        if langfuse.auth_check():
            print("Langfuse client is authenticated and ready!")
        else:
            print("Langfuse authentication failed. Continuing without blocking startup.")
    except Exception as exc:
        print(f"Langfuse check failed ({exc}). Continuing startup without Langfuse readiness check.")


@asynccontextmanager
async def lifespan(app: FastAPI):

    # --- startup logic ---
    OpenAIAgentsInstrumentor().instrument()
    _log_langfuse_readiness()

    yield  # <-- app is running here

    # --- shutdown logic (optional) ---
    print("Shutting down worker...")


app = FastAPI(title="Chat Reports Backend", lifespan=lifespan)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/reports")
def list_reports()-> List[Report]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, created_at
                FROM reports
                ORDER BY id DESC;
                """
            )
            rows = cur.fetchall()
    return [Report(**row) for row in rows]


@app.post("/reports", status_code=201)
def create_report(payload: CreateReportRequest) -> Report:
    title = payload.title.strip() or "New Report"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reports (title)
                VALUES (%s)
                RETURNING id, title, created_at;
                """,
                (title,),
            )
            row = cur.fetchone()
            report_id = row["id"]
            cur.execute(
                """
                INSERT INTO conversations (report_id)
                VALUES (%s);
                """,
                (report_id,),
            )
        conn.commit()
    report = Report(**row)
    write_report_markdown(report)
    return report


@app.post("/reports/{report_id}/title", response_model=Report)
def update_report_title(report_id: int, payload: UpdateReportTitleRequest) -> Report:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Report title is required")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
            cur.execute(
                """
                UPDATE reports
                SET title = %s
                WHERE id = %s
                RETURNING id, title, created_at;
                """,
                (title, report_id),
            )
            row = cur.fetchone()
        conn.commit()
    return Report(**row)


@app.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
            cur.execute("DELETE FROM reports WHERE id = %s;", (report_id,))
        conn.commit()
    delete_report_workspace(report_id)


@app.get("/reports/{report_id}/conversations")
def list_conversations(report_id: int) -> List[Conversation]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
            cur.execute(
                """
                SELECT id, report_id, created_at
                FROM conversations
                WHERE report_id = %s
                ORDER BY id DESC;
                """,
                (report_id,),
            )
            rows = cur.fetchall()
    return [Conversation(**row) for row in rows]


@app.post("/reports/{report_id}/conversations", status_code=201)
def create_conversation(report_id: int) -> Conversation:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
            cur.execute(
                """
                INSERT INTO conversations (report_id)
                VALUES (%s)
                RETURNING id, report_id, created_at;
                """,
                (report_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return Conversation(**row)


@app.get("/conversations/{conversation_id}/messages")
def list_conversation_messages(conversation_id: int) -> List[Message]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            get_conversation(cur, conversation_id)
            cur.execute(
                """
                SELECT m.id, c.report_id, m.role, m.content, m.created_at
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE m.conversation_id = %s
                ORDER BY m.id ASC;
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
    return [Message(**row) for row in rows]


@app.get("/reports/{report_id}/markdown")
def get_report_markdown(report_id: int) -> dict[str, str]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
    return {"content": read_report_markdown(report_id)}


@app.get("/reports/{report_id}/pdf")
async def export_report_pdf(report_id: int):
    report_title = f"report_{report_id}"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM reports WHERE id = %s;", (report_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Report not found")
            report_title = row["title"] or report_title

    pdf_bytes = await render_report_pdf_bytes(report_id)

    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", report_title).strip("._-")
    filename = f"{safe_title or f'report_{report_id}'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/reports/{report_id}/files/{file_path:path}")
def get_report_file(report_id: int, file_path: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)

    workspace = get_report_workspace(report_id)
    safe_file_path = resolve_workspace_relative_path(workspace, file_path)
    if not safe_file_path.exists() or not safe_file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    media_type, _ = mimetypes.guess_type(str(safe_file_path))
    return FileResponse(path=safe_file_path, media_type=media_type)


@app.post("/conversations/{conversation_id}/messages", status_code=201)
async def create_conversation_message(conversation_id: int, payload: CreateMessageRequest):
    user_content = payload.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content is required")

    report_id, history_rows = load_conversation_history(conversation_id)
    ensure_report_markdown_exists(report_id)

    try:
        main_agent = build_main_agent(report_id=report_id)
        agent_input = build_agent_input(history_rows, user_content)
        result = await Runner.run(main_agent, agent_input)
        assistant_content = result.final_output
    except Exception:
        assistant_content = "OpenAI request failed. Your message is stored, but I could not generate a response."

    user_message, assistant_message = persist_message_pair_for_conversation(
        conversation_id=conversation_id,
        report_id=report_id,
        user_content=user_content,
        assistant_content=assistant_content,
    )
    return {"messages": [user_message, assistant_message]}


@app.post("/agent/teach", response_model=TeachAgentResponse, status_code=201)
async def teach_agent(payload: TeachAgentRequest) -> TeachAgentResponse:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Teaching message content is required")

    try:
        skill_agent = build_skill_agent()
        result = await Runner.run(skill_agent, content)
        parsed = parse_skill_agent_output(str(result.final_output))

        if parsed["skill_name"] and parsed["description"] and parsed["skill_markdown"]:
            created = create_skill_from_agent_output(
                skill_name=parsed["skill_name"],
                description=parsed["description"],
                skill_markdown=parsed["skill_markdown"],
            )
        else:
            created = create_skill_from_request(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create shared skill: {exc}") from exc

    return TeachAgentResponse(
        message="Skill created and stored in shared volume",
        skill_filename=created["filename"],
        skill_path=created["skill_md_path"],
    )


@app.get("/skills", response_model=list[Skill])
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


@app.get("/skills/{skill_id}/markdown")
def get_skill_markdown(skill_id: int) -> dict[str, str]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            skill = get_skill(cur, skill_id)
    return {"content": read_skill_markdown(skill)}


@app.post("/skills", response_model=Skill, status_code=201)
def create_skill(payload: CreateSkillRequest) -> Skill:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Skill name is required")
    row = create_skill_row(name=name, description="")
    return Skill(**row)


@app.delete("/skills/{skill_id}", status_code=204)
def delete_skill(skill_id: int) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            skill = get_skill(cur, skill_id)
            cur.execute("DELETE FROM skills WHERE id = %s;", (skill_id,))
        conn.commit()
    delete_skill_filesystem(skill)


@app.get("/skills/{skill_id}/conversations", response_model=list[SkillConversation])
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


@app.post("/skills/{skill_id}/conversations", response_model=SkillConversation, status_code=201)
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


@app.get("/skill-conversations/{skill_conversation_id}/messages", response_model=list[SkillMessage])
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


@app.post("/skill-conversations/{skill_conversation_id}/messages", status_code=201)
async def create_skill_conversation_message(skill_conversation_id: int, payload: CreateMessageRequest):
    user_content = payload.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content is required")

    skill_id, history_rows = load_skill_conversation_history(skill_conversation_id)
    try:
        skill_chat_agent = build_skill_chat_agent()
        agent_input = build_skill_chat_input(history_rows, user_content)
        result = await Runner.run(skill_chat_agent, agent_input)
        assistant_content = str(result.final_output)
    except Exception:
        assistant_content = "I could not process this right now. Please try again."

    user_message, assistant_message = persist_skill_message_pair(
        skill_conversation_id=skill_conversation_id,
        skill_id=skill_id,
        user_content=user_content,
        assistant_content=assistant_content,
    )
    return {"messages": [user_message, assistant_message]}


@app.post("/skills/{skill_id}/publish", response_model=Skill, status_code=200)
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

    history = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    publish_prompt = (
        f"Create/update a skill called '{skill['name']}'.\n"
        f"Current description: {skill['description']}\n"
        "Use this conversation to define the skill:\n"
        f"{history}"
    )

    try:
        skill_agent = build_skill_agent()
        result = await Runner.run(skill_agent, publish_prompt)
        parsed = parse_skill_agent_output(str(result.final_output))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate skill markdown: {exc}") from exc

    if not parsed["skill_name"] or not parsed["description"] or not parsed["skill_markdown"]:
        raise HTTPException(status_code=500, detail="Skill generation returned incomplete output")

    created = create_skill_from_agent_output(
        skill_name=parsed["skill_name"],
        description=parsed["description"],
        skill_markdown=parsed["skill_markdown"],
    )

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
                    parsed["skill_name"],
                    parsed["description"],
                    slugify(parsed["skill_name"]),
                    created["skill_md_path"],
                    skill_id,
                ),
            )
            updated = cur.fetchone()
        conn.commit()
    return Skill(**updated)


@app.get("/agent/skills", response_model=list[SkillSummary])
def list_agent_skills() -> list[SkillSummary]:
    # Backward-compatible endpoint for existing UI consumers.
    return [SkillSummary(**item) for item in list_existing_skills()]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


if __name__ == "__main__":

    from dotenv import load_dotenv
    if os.getenv("APP_ENV") != "docker":
        load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")
        
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get("/health")
        print(response.status_code)
        print(response.json())
