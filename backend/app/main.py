import os
from typing import Any, List, Literal, Optional
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from agents import Runner

from .schemas import Report, Message, CreateReportRequest, CreateMessageRequest
from .agent import build_main_agent


database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/reporting",
)
pool = ConnectionPool(conninfo=database_url, kwargs={"row_factory": dict_row})


from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client
from contextlib import asynccontextmanager
from dotenv import load_dotenv


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup logic ---
    load_dotenv("../.env")
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
async def create_message(report_id: int, payload: CreateMessageRequest):

    user_content = payload.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content is required")

    try:
        main_agent = build_main_agent()
        result = await Runner.run(main_agent, user_content)
        assistant_content = result.final_output
    except Exception:
        assistant_content = "OpenAI request failed. Your message is stored, but I could not generate a response."

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
                (conversation_id, user_content, report_id),
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
