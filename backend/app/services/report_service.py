from typing import Any

from agents import Runner

from app.agents.reporting_agent import build_reporting_agent
from app.utils.report_utils import (
    build_agent_input,
    ensure_report_markdown_exists,
    load_conversation_history,
    persist_message_pair_for_conversation,
    render_report_pdf_bytes,
)


async def export_report_pdf_bytes(report_id: int) -> bytes:
    return await render_report_pdf_bytes(report_id)


async def run_report_conversation_turn(conversation_id: int, user_content: str) -> dict[str, list[Any]]:
    report_id, history_rows = load_conversation_history(conversation_id)
    ensure_report_markdown_exists(report_id)

    try:
        reporting_agent = build_reporting_agent(report_id=report_id)
        agent_input = build_agent_input(history_rows, user_content)
        result = await Runner.run(reporting_agent, agent_input)
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
