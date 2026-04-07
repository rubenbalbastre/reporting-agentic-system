import os
from typing import Any, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from langfuse import Langfuse

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .schemas import Report, Message, CreateReportRequest, CreateMessageRequest
from .graph import ReportingAgentGraph


app = FastAPI(title="Chat Reports Backend")
langfuse_client: Optional[Langfuse] = None
openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
reporting_agent: Optional[ReportingAgentGraph] = None
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/reporting",
)
pool = ConnectionPool(conninfo=database_url, kwargs={"row_factory": dict_row})


def init_langfuse() -> None:
    global langfuse_client
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://langfuse-web:3000")
    if public_key and secret_key:
        langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )


def start_trace(name: str, input_data: Any, metadata: Optional[dict[str, Any]] = None):
    if not langfuse_client:
        return None
    try:
        return langfuse_client.trace(name=name, input=input_data, metadata=metadata or {})
    except Exception:
        return None


@app.on_event("startup")
def on_startup() -> None:
    init_langfuse()


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
    trace = start_trace(
        "create_message",
        input_data={"report_id": report_id, "content": payload.content},
        metadata={"model": openai_model},
    )
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message content is required")

    assistant_content = f"Got it. You said: {content}"
    generation = trace.generation(name="openai_response") if trace else None
    try:
        reporting_agent = ReportingAgentGraph(model_name=openai_model)
        response = await reporting_agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise analytics reporting assistant helping refine report drafts.",
                    },
                    {"role": "user", "content": content},
                ]
            }
        )
        generated = (response.get("output_text") or "").strip()
        if generated:
            assistant_content = generated
        if generation:
            generation.end(output=assistant_content)
    except Exception:
        assistant_content = "OpenAI request failed. Your message is stored, but I could not generate a response."
        if trace:
            trace.event(name="openai_error", input={"report_id": report_id})

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
    if trace:
        trace.update(
            output={
                "report_id": report_id,
                "user_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
            }
        )
    return {"messages": [user_message, assistant_message]}


@app.on_event("shutdown")
def on_shutdown() -> None:
    if langfuse_client:
        try:
            langfuse_client.flush()
        except Exception:
            pass
    pool.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}
