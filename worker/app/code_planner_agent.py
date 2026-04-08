from dotenv import load_dotenv
from agents import Agent, function_tool
from pydantic import BaseModel

from .database_agent import build_database_agent
from .common_tools import think_tool


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Literal, List, Optional


class PlanStep(BaseModel):
    step_id: int
    action: Literal["list_files", "read_file", "write_file", "run_python", "think_tool"]
    target: Optional[str] = None
    reason: str


class CodePlan(BaseModel):
    status: Literal["needs_more_info", "ready_to_execute"]
    missing_information: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    steps: List[PlanStep] = Field(default_factory=list)


def build_code_planner_agent() -> Agent:
    load_dotenv("../.env")
    return Agent(
        name="Code planner",
        instructions=(
            "You are a code planner. Your task is to create a high-level plan for writing a Python script that answers the user's question. "
            "Your plan should break down the problem into smaller steps, identify what functions or classes to create, and outline the logic flow."
            "This plan will guide the code assistant in implementing the solution."
            "You must inspect the database schema to be able to create a good plan."
            "Extra notes:"
            "Do not waste steps on basic Python syntax or trivial code. Focus on the high-level structure and logic of the code needed to solve the problem."
            "It is ok if the plan has few steps. The code assistant can fill in details. The important thing is to have a clear structure and logic flow."
        ),
        model="gpt-5.4-nano",
        output_type=CodePlan,
        tools=[
            build_database_agent().as_tool(
                tool_name="database_agent",
                tool_description="Tool to inspect the database and decide if user's question can be answered with it."
            ),
            think_tool
        ]
    )

