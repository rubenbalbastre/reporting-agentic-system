import subprocess
from pathlib import Path
from agents import Agent, function_tool

from .common_tools import think_tool, finish_tool


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------


def build_code_executor_agent(workspace_dir: str) -> Agent:
    workspace = Path(workspace_dir).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    def safe_path(rel_path: str) -> Path:
        candidate = (workspace / rel_path).resolve()
        if not str(candidate).startswith(str(workspace)):
            raise ValueError("Path escapes workspace")
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

    code_agent = Agent(
        name="Code assistant",
        instructions=(
            "You are a code assistant which is given a plan with steps to implement a Python script that answers the user's question. "
            "Write Python scripts into the workspace, inspect files when needed, "
            "and execute them with run_python. "
            "Prefer an iterative loop: inspect -> write -> run -> fix. "
            "Do not claim code works unless you executed it successfully."
            "You can get postgress database url from DATABASE_URL environment variable and connect to it to inspect the schema or run queries if needed. "
        ),
        model="gpt-5.4-nano",
        tools=[
            think_tool, finish_tool,
            write_file, read_file, list_files,
            run_python
        ]
    )
    return code_agent
