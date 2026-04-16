from agents import Runner
from fastapi import HTTPException

from app.agents.skill_agent import build_skill_agent, build_skill_chat_agent
from app.utils.skill_utils import (
    build_skill_chat_input,
    load_skill_conversation_history,
    parse_skill_agent_output,
    persist_skill_message_pair,
)
from app.utils.skills import create_skill_from_agent_output, create_skill_from_request, slugify


async def teach_and_create_skill(content: str) -> dict[str, str]:
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

    return {
        "message": "Skill created and stored in shared volume",
        "skill_filename": created["filename"],
        "skill_path": created["skill_md_path"],
    }


async def run_skill_conversation_turn(skill_conversation_id: int, user_content: str) -> dict[str, list[dict]]:
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


async def generate_published_skill(skill: dict, messages: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
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

    update_fields = {
        "name": parsed["skill_name"],
        "description": parsed["description"],
        "slug": slugify(parsed["skill_name"]),
        "skill_md_path": created["skill_md_path"],
    }
    return created, update_fields
