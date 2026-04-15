from agents import Agent, function_tool
from pydantic import BaseModel

from app.agents.database_agent import build_database_agent
from app.agents.instructions import load_agent_notes
from app.agents.prompts import build_code_planner_instructions
from app.utils.shared_skills import search_shared_skills, read_shared_skill


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Literal, List, Optional


class PlanStep(BaseModel):
    step_id: int
    action: Literal["list_files", "read_file", "write_file", "run_python"]
    target: Optional[str] = None
    reason: str


class CodePlan(BaseModel):
    status: Literal["needs_more_info", "ready_to_execute"]
    missing_information: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    steps: List[PlanStep] = Field(default_factory=list)
    skills_to_apply: List[str] = Field(default_factory=list)
    skill_notes: Optional[str] = None


def build_code_planner_agent() -> Agent:
    @function_tool
    def search_agent_skills(query: str) -> str:
        """Search shared skills by keyword and return matching skill IDs and previews."""
        results = search_shared_skills(query=query, limit=10)
        if not results:
            return "No shared skills found"
        lines = []
        for item in results:
            lines.append(f"- {item['skill_id']} | {item['title']}: {item['preview']}")
        return "\n".join(lines)

    @function_tool
    def read_agent_skill(skill_name: str) -> str:
        """Read one shared skill by skill directory name."""
        try:
            return read_shared_skill(skill_name)
        except FileNotFoundError as exc:
            return f"Skill not found: {exc}"

    additional_instructions = load_agent_notes()
    return Agent(
        name="code_planner",
        instructions=build_code_planner_instructions(additional_instructions),
        model="gpt-5.4-nano",
        output_type=CodePlan,
        tools=[
            build_database_agent().as_tool(
                tool_name="database_agent",
                tool_description="Tool to inspect the database and decide if user's question can be answered with it."
            ),
            search_agent_skills,
            read_agent_skill,
        ]
    )
