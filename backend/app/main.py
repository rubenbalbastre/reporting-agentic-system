import os
import mimetypes
from typing import Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import psycopg2
from psycopg2.extras import RealDictCursor
from agents import Runner
from pathlib import Path
from app.schemas import Report, Message, CreateReportRequest, CreateMessageRequest
from app.agent import build_main_agent
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


def _load_report_history(report_id: int) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _ensure_report_exists(cur, report_id)
            cur.execute(
                """
                SELECT m.role, m.content
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.report_id = %s
                ORDER BY m.id ASC;
                """,
                (report_id,),
            )
            return cur.fetchall()


def _get_or_create_conversation_id(cur: Any, report_id: int) -> int:
    cur.execute(
        """
        SELECT id
        FROM conversations
        WHERE report_id = %s
        ORDER BY id ASC
        LIMIT 1;
        """,
        (report_id,),
    )
    conversation = cur.fetchone()
    if conversation is not None:
        return conversation["id"]

    cur.execute(
        "INSERT INTO conversations (report_id) VALUES (%s) RETURNING id;",
        (report_id,),
    )
    return cur.fetchone()["id"]


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


def _persist_message_pair(report_id: int, user_content: str, assistant_content: str) -> tuple[Message, Message]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            _ensure_report_exists(cur, report_id)
            conversation_id = _get_or_create_conversation_id(cur, report_id)
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


@app.get("/reports/{report_id}/messages")
def list_messages(report_id: int) -> List[Message]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM reports WHERE id = %s;", (report_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Report not found")
            cur.execute(
                """
                SELECT m.id, c.report_id, m.role, m.content, m.created_at
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.report_id = %s
                ORDER BY m.id ASC;
                """,
                (report_id,),
            )
            rows = cur.fetchall()
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


@app.post("/reports/{report_id}/messages", status_code=201)
async def create_message(report_id: int, payload: CreateMessageRequest):

    user_content = payload.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content is required")

    history_rows = _load_report_history(report_id)
    _ensure_report_markdown_exists(report_id)

    try:
        main_agent = build_main_agent(report_id=report_id)
        agent_input = _build_agent_input(history_rows, user_content)
        result = await Runner.run(main_agent, agent_input)
        assistant_content = result.final_output
    except Exception:
        assistant_content = "OpenAI request failed. Your message is stored, but I could not generate a response."

    user_message, assistant_message = _persist_message_pair(
        report_id=report_id,
        user_content=user_content,
        assistant_content=assistant_content,
    )

    return {"messages": [user_message, assistant_message]}


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
