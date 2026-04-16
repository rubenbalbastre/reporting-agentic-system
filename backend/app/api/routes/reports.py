import mimetypes
import re
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.schemas import (
    Conversation,
    CreateMessageRequest,
    CreateReportRequest,
    Message,
    Report,
    UpdateReportTitleRequest,
)
from app.services.report_service import export_report_pdf_bytes, run_report_conversation_turn
from app.utils.db import get_db_connection
from app.utils.report_utils import (
    delete_report_workspace,
    ensure_report_exists,
    get_conversation,
    read_report_markdown,
    write_report_markdown,
)
from app.utils.workspace_paths import get_report_workspace, resolve_workspace_relative_path

router = APIRouter()


@router.get("/reports")
def list_reports() -> List[Report]:
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


@router.post("/reports", status_code=201)
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


@router.post("/reports/{report_id}/title", response_model=Report)
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


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int) -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
            cur.execute("DELETE FROM reports WHERE id = %s;", (report_id,))
        conn.commit()
    delete_report_workspace(report_id)


@router.get("/reports/{report_id}/conversations")
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


@router.post("/reports/{report_id}/conversations", status_code=201)
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


@router.get("/conversations/{conversation_id}/messages")
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


@router.get("/reports/{report_id}/markdown")
def get_report_markdown(report_id: int) -> dict[str, str]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
    return {"content": read_report_markdown(report_id)}


@router.get("/reports/{report_id}/pdf")
async def export_report_pdf(report_id: int):
    report_title = f"report_{report_id}"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM reports WHERE id = %s;", (report_id,))
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Report not found")
            report_title = row["title"] or report_title

    pdf_bytes = await export_report_pdf_bytes(report_id)

    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", report_title).strip("._-")
    filename = f"{safe_title or f'report_{report_id}'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{report_id}/files/{file_path:path}")
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


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def create_conversation_message(conversation_id: int, payload: CreateMessageRequest):
    user_content = payload.content.strip()
    if not user_content:
        raise HTTPException(status_code=400, detail="Message content is required")

    return await run_report_conversation_turn(conversation_id=conversation_id, user_content=user_content)
