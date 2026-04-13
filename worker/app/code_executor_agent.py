import subprocess
from pathlib import Path
from agents import Agent, function_tool

from app.common_tools import think_tool
from app.database_agent import (
    get_database_schema,
    get_unique_values,
    get_column_stats,
    preview_table
)
from app.instructions import load_agent_notes
from app.prompts import build_code_executor_instructions
from app.shared_skills import search_shared_skills, read_shared_skill


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------


def build_code_executor_agent(workspace_dir: str) -> Agent:
    workspace = Path(workspace_dir).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    def safe_path(rel_path: str) -> Path:
        raw = Path(rel_path)
        if raw.is_absolute():
            raise ValueError("Path must be relative to workspace")

        candidate = (workspace / raw).resolve()
        try:
            candidate.relative_to(workspace)
        except ValueError as exc:
            raise ValueError("Path escapes workspace") from exc
        return candidate

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
            rel = p.relative_to(workspace)
            suffix = "/" if p.is_dir() else ""
            items.append(f"{rel}{suffix}")
        return "\n".join(items) if items else "(empty)"

    @function_tool
    def run_python(entrypoint: str, timeout: int = 10) -> str:
        """
        Execute a Python file from the workspace and return stdout/stderr.
            - entrypoint: path to the Python file to execute, relative to the workspace.
            - timeout: maximum execution time in seconds.
        """
        file_path = safe_path(entrypoint)
        if not file_path.exists():
            return f"ERROR: {entrypoint} does not exist"

        result = subprocess.run(
            ["python", str(file_path)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (
            f"exit_code={result.returncode}\n"
            f"--- STDOUT ---\n{result.stdout}\n"
            f"--- STDERR ---\n{result.stderr}"
        )

    @function_tool
    def search_agent_skills(query: str) -> str:
        """Search shared skills by keyword and return matching filenames and previews."""
        results = search_shared_skills(query=query, limit=10)
        if not results:
            return "No shared skills found"
        lines = []
        for item in results:
            lines.append(f"- {item['filename']}: {item['preview']}")
        return "\n".join(lines)

    @function_tool
    def read_agent_skill(filename: str) -> str:
        """Read one shared skill file by filename."""
        try:
            return read_shared_skill(filename)
        except FileNotFoundError as exc:
            return f"Skill not found: {exc}"

    additional_instructions = load_agent_notes()
    code_agent = Agent(
        name="code_assistant",
        instructions=build_code_executor_instructions(additional_instructions),
        model="gpt-5.4-nano",
        tools=[
            # think_tool,
            write_file, read_file, list_files,
            run_python,
            get_database_schema,
            get_unique_values,
            get_column_stats,
            preview_table,
            search_agent_skills,
            read_agent_skill,
        ]
    )
    return code_agent
