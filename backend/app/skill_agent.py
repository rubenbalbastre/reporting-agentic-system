from agents import Agent
from app.prompts import build_skill_agent_instructions, build_skill_chat_agent_instructions


def build_skill_agent() -> Agent:
    return Agent(
        name="skill_agent",
        instructions=build_skill_agent_instructions(),
        model="gpt-5.4-nano",
    )


def build_skill_chat_agent() -> Agent:
    return Agent(
        name="skill_chat_agent",
        instructions=build_skill_chat_agent_instructions(),
        model="gpt-5.4-nano",
    )
