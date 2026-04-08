from dotenv import load_dotenv
import subprocess
from pathlib import Path
from agents import Agent, function_tool


load_dotenv("../.env")


# -------------------------------------------------------------------
# Tools
# -------------------------------------------------------------------


@function_tool
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"


@function_tool
def finish_tool():
    """Tool to signal completition of the task"""
    return "Task completed"



# -------------------------------------------------------------------
# Workspace
# -------------------------------------------------------------------

WORKSPACE = Path("./workspace")
WORKSPACE.mkdir(exist_ok=True)


def safe_path(rel_path: str) -> Path:
    """
    Resolve a workspace-relative path and prevent escaping the sandbox.
    """
    candidate = (WORKSPACE / rel_path).resolve()
    workspace_root = WORKSPACE.resolve()

    if not str(candidate).startswith(str(workspace_root)):
        raise ValueError("Path escapes workspace")

    return candidate


# -------------------------------------------------------------------
# File system tools
# -------------------------------------------------------------------

@function_tool
def write_file(path: str, content: str) -> str:
    """Write text content to a file inside the workspace."""
    file_path = safe_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Wrote {path}"


@function_tool
def read_file(path: str) -> str:
    """Read a text file from the workspace."""
    file_path = safe_path(path)
    return file_path.read_text(encoding="utf-8")


@function_tool
def list_files(path: str = ".") -> str:
    """List files recursively inside a workspace directory."""
    dir_path = safe_path(path)
    if not dir_path.exists():
        return f"{path} does not exist"

    if dir_path.is_file():
        return path

    items = []
    for p in sorted(dir_path.rglob("*")):
        rel = p.relative_to(WORKSPACE)
        suffix = "/" if p.is_dir() else ""
        items.append(f"{rel}{suffix}")

    return "\n".join(items) if items else "(empty)"


# -------------------------------------------------------------------
# Execution tool
# -------------------------------------------------------------------

@function_tool
def run_python(entrypoint: str, timeout: int = 10) -> str:
    """
    Execute a Python file from the workspace and return stdout/stderr.
    """
    file_path = safe_path(entrypoint)

    if not file_path.exists():
        return f"ERROR: {entrypoint} does not exist"

    result = subprocess.run(
        ["python", str(file_path)],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return (
        f"exit_code={result.returncode}\n"
        f"--- STDOUT ---\n{result.stdout}\n"
        f"--- STDERR ---\n{result.stderr}"
    )


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
    return Agent(
        name="Code planner",
        instructions=(
            "You are a code planner. Your task is to create a high-level plan for writing a Python script that answers the user's question. "
            "Your plan should break down the problem into smaller steps, identify what functions or classes to create, and outline the logic flow."
            "This plan will guide the code assistant in implementing the solution."
            "Do not waste steps on basic Python syntax or trivial code. Focus on the high-level structure and logic of the code needed to solve the problem."
            "It is ok if the plan has few steps. The code assistant can fill in details. The important thing is to have a clear structure and logic flow."
        ),
        model="gpt-5.4-nano",
        output_type=CodePlan
    )


def build_code_executor_agent() -> Agent:
    code_agent = Agent(
        name="Code assistant",
        instructions=(
            "You are a code assistant which is given a plan with steps to implement a Python script that answers the user's question. "
            "Write Python scripts into the workspace, inspect files when needed, "
            "and execute them with run_python. "
            "Prefer an iterative loop: inspect -> write -> run -> fix. "
            "Do not claim code works unless you executed it successfully."
        ),
        model="gpt-5.4-nano",
        tools=[
            think_tool, finish_tool,
            write_file, read_file, list_files,
            run_python
        ]
    )
    return code_agent
