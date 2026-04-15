import base64
import mimetypes
import os
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from markdown import markdown
from playwright.async_api import async_playwright

from app.utils.db import get_db_connection
from app.schemas import Message, Report
from app.utils.workspace_paths import get_report_markdown_path, get_report_workspace, resolve_workspace_relative_path


def build_agent_input(history_rows: list[dict[str, Any]], user_content: str, max_messages: int = 20) -> str:
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


def ensure_report_exists(cur: Any, report_id: int) -> None:
    cur.execute("SELECT id FROM reports WHERE id = %s;", (report_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Report not found")


def get_conversation(cur: Any, conversation_id: int) -> dict[str, Any]:
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


def load_conversation_history(conversation_id: int) -> tuple[int, list[dict[str, Any]]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            conversation = get_conversation(cur, conversation_id)
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


def persist_message_pair_for_conversation(
    conversation_id: int, report_id: int, user_content: str, assistant_content: str
) -> tuple[Message, Message]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            ensure_report_exists(cur, report_id)
            get_conversation(cur, conversation_id)
            user_row = _insert_message(cur, conversation_id, report_id, "user", user_content)
            assistant_row = _insert_message(cur, conversation_id, report_id, "assistant", assistant_content)
        conn.commit()

    return Message(**user_row), Message(**assistant_row)


def write_report_markdown(report: Report) -> None:
    report_path = get_report_markdown_path(report.id)
    content = (
        f"# {report.title}\n\n"
        f"- Report ID: {report.id}\n"
        f"- Created At: {report.created_at.isoformat()}\n"
    )
    report_path.write_text(content, encoding="utf-8")


def ensure_report_markdown_exists(report_id: int) -> None:
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

    write_report_markdown(Report(**row))


def read_report_markdown(report_id: int) -> str:
    ensure_report_markdown_exists(report_id)
    report_path = get_report_markdown_path(report_id)
    return report_path.read_text(encoding="utf-8")


def report_markdown_to_html(report_id: int, content: str) -> str:
    workspace = get_report_workspace(report_id).resolve()
    html_body = markdown(content, extensions=["tables", "fenced_code", "toc"])

    def _replace_src(match: re.Match[str]) -> str:
        src = match.group(1)
        rel: str | None = None
        files_prefix = f"/reports/{report_id}/files/"
        figures_prefix = f"/reports/{report_id}/figures/"

        if src.startswith(files_prefix):
            rel = src[len(files_prefix):]
        elif src.startswith(figures_prefix):
            rel = f"figures/{src[len(figures_prefix):]}"
        elif src.startswith("figures/"):
            rel = src
        else:
            return match.group(0)

        try:
            safe_file_path = resolve_workspace_relative_path(workspace, rel)
            if not safe_file_path.exists() or not safe_file_path.is_file():
                return match.group(0)
            mime_type, _ = mimetypes.guess_type(str(safe_file_path))
            if not mime_type:
                mime_type = "application/octet-stream"
            raw = safe_file_path.read_bytes()
            encoded = base64.b64encode(raw).decode("ascii")
            return f'src="data:{mime_type};base64,{encoded}"'
        except Exception:
            return match.group(0)

    html_body = re.sub(r'src="([^"]+)"', _replace_src, html_body)

    return f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <style>
      @page {{ size: A4; margin: 18mm; }}
      body {{
        font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Arial, sans-serif;
        color: #111827;
        line-height: 1.6;
        font-size: 13px;
      }}
      h1, h2, h3 {{ color: #0f172a; line-height: 1.25; }}
      img {{ max-width: 100%; height: auto; page-break-inside: avoid; }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 12px;
      }}
      th, td {{
        border: 1px solid #d1d5db;
        padding: 6px 8px;
        vertical-align: top;
      }}
      th {{ background: #f3f4f6; }}
      code {{
        background: #f3f4f6;
        padding: 1px 4px;
        border-radius: 4px;
      }}
      pre {{
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 10px;
        overflow: auto;
      }}
    </style>
  </head>
  <body>
    {html_body}
  </body>
</html>"""


async def render_report_pdf_bytes(report_id: int) -> bytes:
    markdown_text = read_report_markdown(report_id)
    html_content = report_markdown_to_html(report_id, markdown_text)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
            await browser.close()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render PDF. Ensure Playwright Chromium is installed. Error: {exc}",
        ) from exc

    return pdf_bytes


def delete_report_workspace(report_id: int) -> None:
    try:
        workspace_root = Path(os.getenv("WORKSPACE_ROOT", "/data/shared/jobs")).resolve()
        report_workspace = (workspace_root / f"report_{report_id}").resolve()
        if report_workspace.exists() and report_workspace.is_dir():
            shutil.rmtree(report_workspace, ignore_errors=True)
    except Exception:
        pass
