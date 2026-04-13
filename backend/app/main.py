import os
import mimetypes
import json
from typing import Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import psycopg2
from psycopg2.extras import RealDictCursor
from agents import Runner
from pathlib import Path
from app.schemas import (
    Report,
    Conversation,
    Message,
    CreateReportRequest,
    CreateMessageRequest,
    TeachAgentRequest,
    TeachAgentResponse,
    SkillSummary,
)
from app.agent import build_main_agent
from app.skill_agent import build_skill_agent
from app.skills import create_skill_from_request, create_skill_from_agent_output, list_existing_skills
from app.workspace_paths import get_report_markdown_path, get_report_workspace, resolve_workspace_relative_path
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client
from contextlib import asynccontextmanager


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


@asynccontextmanager
async def lifespan(app: FastAPI):

    # --- startup logic ---
    OpenAIAgentsInstrumentor().instrument()

    langfuse = get_client()
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")

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


def _build_agent_input(history_rows: list[dict[str, Any]], user_content: str, max_messages: int = 20) -> str:
    recent = history_rows[-max_messages:]
    lines = []
    for row in recent:
        role = row["role"]
        content = row["content"]
        lines.append(f"{role}: {content}")
    lines.append(f"user: {user_content}")
    history_text = "\n".join(lines) if lines else f"user: {user_content}"
    return (
        "Use the conversation history to keep context consistent.\n"
        "Conversation:\n"
        f"{history_text}"
    )


def _ensure_report_exists(cur: Any, report_id: int) -> None:
    cur.execute("SELECT id FROM reports WHERE id = %s;", (report_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Report not found")


def _get_conversation(cur: Any, conversation_id: int) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, report_id, created_at
        FROM conversations
        WHERE id = %s;
        """,
        (conversation_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return row


def _load_conversation_history(conversation_id: int) -> tuple[int, list[dict[str, Any]]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            conversation = _get_conversation(cur, conversation_id)
            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY id ASC;
                """,
                (conversation_id,),
            )
            return conversation["report_id"], cur.fetchall()


def _insert_message(cur: Any, conversation_id: int, report_id: int, role: str, content: str) -> dict[str, Any]:
    cur.execute(
        """
        INSERT INTO messages (conversation_id, role, content)
        VALUES (%s, %s, %s)
        RETURNING id, %s AS report_id, role, content, created_at;
        """,
        (conversation_id, role, content, report_id),
    )
    return cur.fetchone()


def _persist_message_pair_for_conversation(
    conversation_id: int, report_id: int, user_content: str, assistant_content: str
) -> tuple[Message, Message]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _ensure_report_exists(cur, report_id)
            _get_conversation(cur, conversation_id)
            user_row = _insert_message(cur, conversation_id, report_id, "user", user_content)
            assistant_row = _insert_message(cur, conversation_id, report_id, "assistant", assistant_content)
        conn.commit()

    return Message(**user_row), Message(**assistant_row)


def _write_report_markdown(report: Report) -> None:
    report_path = get_report_markdown_path(report.id)
    content = (
        f"# {report.title}\n\n"
        f"- Report ID: {report.id}\n"
        f"- Created At: {report.created_at.isoformat()}\n"
    )
    report_path.write_text(content, encoding="utf-8")


def _ensure_report_markdown_exists(report_id: int) -> None:
    report_path = get_report_markdown_path(report_id)
    if report_path.exists():
        return

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, created_at
                FROM reports
                WHERE id = %s;
                """,
                (report_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Report not found")

    _write_report_markdown(Report(**row))


def _read_report_markdown(report_id: int) -> str:
    _ensure_report_markdown_exists(report_id)
    report_path = get_report_markdown_path(report_id)
    return report_path.read_text(encoding="utf-8")


def _parse_skill_agent_output(raw_output: str) -> dict[str, str]:
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
    _write_report_markdown(report)
    return report


@app.get("/reports/{report_id}/conversations")
def list_conversations(report_id: int) -> List[Conversation]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _ensure_report_exists(cur, report_id)
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
            _ensure_report_exists(cur, report_id)
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
            conversation = _get_conversation(cur, conversation_id)
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
    _ = conversation
    return [Message(**row) for row in rows]


@app.get("/reports/{report_id}/markdown")
def get_report_markdown(report_id: int) -> dict[str, str]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _ensure_report_exists(cur, report_id)
    return {"content": _read_report_markdown(report_id)}


@app.get("/reports/{report_id}/files/{file_path:path}")
def get_report_file(report_id: int, file_path: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _ensure_report_exists(cur, report_id)

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

    report_id, history_rows = _load_conversation_history(conversation_id)
    _ensure_report_markdown_exists(report_id)

    try:
        main_agent = build_main_agent(report_id=report_id)
        agent_input = _build_agent_input(history_rows, user_content)
        result = await Runner.run(main_agent, agent_input)
        assistant_content = result.final_output
    except Exception:
        assistant_content = "OpenAI request failed. Your message is stored, but I could not generate a response."

    user_message, assistant_message = _persist_message_pair_for_conversation(
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
        parsed = _parse_skill_agent_output(str(result.final_output))

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


@app.get("/agent/skills", response_model=list[SkillSummary])
def list_agent_skills() -> list[SkillSummary]:
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

        response = client.post("/reports/50/messages", json={
            "report_id": 50,
            "payload": {"content": "Can you answer questions about total sales by product category for january 2017?"},
        })
        print(response.status_code)
        print(response.json())
