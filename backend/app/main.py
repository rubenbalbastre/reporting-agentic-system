import os
from datetime import datetime
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

app = FastAPI(title="Chat Reports Backend")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@app:5432/reporting",
)
pool = ConnectionPool(conninfo=database_url, kwargs={"row_factory": dict_row})


class Report(BaseModel):
    id: int
    title: str
    created_at: datetime


class Message(BaseModel):
    id: int
    report_id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class CreateReportRequest(BaseModel):
    title: str = "New Report"


class CreateMessageRequest(BaseModel):
    content: str


def init_db() -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id BIGSERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id BIGSERIAL PRIMARY KEY,
                    report_id BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("SELECT COUNT(*) AS count FROM reports;")
            count = cur.fetchone()["count"]
            if count == 0:
                cur.execute(
                    "INSERT INTO reports (title) VALUES (%s) RETURNING id;",
                    ("First Report",),
                )
                report_id = cur.fetchone()["id"]
                cur.execute(
                    "INSERT INTO conversations (report_id) VALUES (%s);",
                    (report_id,),
                )
        conn.commit()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/reports")
def list_reports() -> List[Report]:
    with pool.connection() as conn:
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


@app.post("/api/reports", status_code=201)
def create_report(payload: CreateReportRequest) -> Report:
    title = payload.title.strip() or "New Report"
    with pool.connection() as conn:
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
    return Report(**row)


@app.get("/api/reports/{report_id}/messages")
def list_messages(report_id: int) -> List[Message]:
    with pool.connection() as conn:
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


@app.post("/api/reports/{report_id}/messages", status_code=201)
def create_message(report_id: int, payload: CreateMessageRequest):
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content is required")

    assistant_content = f"Got it. You said: {content}"

    if openai_client:
        try:
            response = openai_client.responses.create(
                model=openai_model,
                input=[
                    {
                        "role": "system",
                        "content": "You are a concise analytics reporting assistant helping refine report drafts.",
                    },
                    {"role": "user", "content": content},
                ],
            )
            generated = (response.output_text or "").strip()
            if generated:
                assistant_content = generated
        except Exception:
            assistant_content = "OpenAI request failed. Your message is stored, but I could not generate a response."
    else:
        assistant_content = "I stored your message. Add OPENAI_API_KEY to enable AI responses."

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM reports WHERE id = %s;", (report_id,))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Report not found")

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
            if conversation is None:
                cur.execute(
                    "INSERT INTO conversations (report_id) VALUES (%s) RETURNING id;",
                    (report_id,),
                )
                conversation_id = cur.fetchone()["id"]
            else:
                conversation_id = conversation["id"]

            cur.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (%s, 'user', %s)
                RETURNING id, %s AS report_id, role, content, created_at;
                """,
                (conversation_id, content, report_id),
            )
            user_row = cur.fetchone()

            cur.execute(
                """
                INSERT INTO messages (conversation_id, role, content)
                VALUES (%s, 'assistant', %s)
                RETURNING id, %s AS report_id, role, content, created_at;
                """,
                (conversation_id, assistant_content, report_id),
            )
            assistant_row = cur.fetchone()
        conn.commit()

    user_message = Message(**user_row)
    assistant_message = Message(**assistant_row)
    return {"messages": [user_message, assistant_message]}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}
