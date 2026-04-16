from agents import Runner
from fastapi import HTTPException
from pathlib import Path

from app.agents.skill_agent import build_skill_agent
from app.utils.skill_utils import (
    build_skill_chat_input,
    is_published_skill_path,
    load_skill_conversation_history,
    parse_skill_agent_output,
    persist_skill_message_pair,
)
from app.utils.skills import (
    create_skill_from_agent_output,
    create_skill_from_request,
    publish_skill_draft,
    slugify,
)


async def teach_and_create_skill(content: str) -> dict[str, str]:
    try:
        skill_agent = build_skill_agent(skill_session_id="skill_quick_teach")
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

    return {
        "message": "Skill created and stored in shared volume",
        "skill_filename": created["filename"],
        "skill_path": created["skill_md_path"],
    }


async def run_skill_conversation_turn(skill_conversation_id: int, user_content: str) -> dict[str, list[dict]]:
    skill_id, skill_md_path, history_rows = load_skill_conversation_history(skill_conversation_id)
    if is_published_skill_path(skill_md_path):
        raise HTTPException(status_code=400, detail="Published skill is read-only. Use 'Open in Draft' first.")
    try:
        skill_workspace = str(Path(skill_md_path).resolve().parent)
        skill_chat_agent = build_skill_agent(
            skill_session_id=f"skill_{skill_id}",
            workspace_path=skill_workspace,
        )
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


async def generate_published_skill(skill: dict, messages: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    _ = messages
    skill_md_path = (skill.get("skill_md_path") or "").strip()
    if not skill_md_path:
        raise HTTPException(status_code=500, detail="Skill draft path missing for publish")

    try:
        created = publish_skill_draft(skill_md_path=skill_md_path)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to publish skill draft: {exc}") from exc

    update_fields = {
        "name": created["name"],
        "description": created["description"],
        "slug": slugify(created["name"]),
        "skill_md_path": created["skill_md_path"],
    }
    return created, update_fields
