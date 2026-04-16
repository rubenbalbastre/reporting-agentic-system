import subprocess
import mimetypes
from pathlib import Path
from agents import Agent, function_tool
from openai import OpenAI

from app.agents.database_agent import (
    get_database_schema,
    get_unique_values,
    get_column_stats,
    preview_table
)
from app.agents.instructions import load_agent_notes
from app.agents.prompts import build_code_executor_instructions
from app.utils.shared_skills import search_shared_skills, read_shared_skill
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------


class CodeAgentResult(BaseModel):
    status: Literal["needs_more_info", "ready_to_execute"]
    missing_information: List[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    summary: str


def build_code_executor_agent(workspace_dir: str, task_type: Literal["report", "skill"] = "report") -> Agent:
    workspace = Path(workspace_dir).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    def _is_probably_text(file_path: Path) -> bool:
        try:
            sample = file_path.read_bytes()[:4096]
        except Exception:
            return False
        if b"\x00" in sample:
            return False
        if not sample:
            return True
        non_printable = sum(1 for b in sample if b < 9 or (13 < b < 32))
        return (non_printable / len(sample)) < 0.20

    def _upload_image_for_reasoning(file_path: Path, display_path: str | None = None) -> str:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        with file_path.open("rb") as fh:
            uploaded = client.files.create(file=fh, purpose="assistants")
        label = display_path or str(file_path.relative_to(workspace))
        return f"path={label} file_id={uploaded.id} mime={mime_type or 'application/octet-stream'}"

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
        if not file_path.exists() or not file_path.is_file():
            return f"ERROR: {path} does not exist"
        if not _is_probably_text(file_path):
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith("image/"):
                try:
                    uploaded_note = _upload_image_for_reasoning(file_path, display_path=path)
                    return (
                        f"IMAGE_FILE_UPLOADED {uploaded_note}. "
                        "Use this uploaded image file for visual reasoning."
                    )
                except Exception as exc:
                    return f"ERROR: Failed to upload image {path} to OpenAI files API: {exc}"
            return (
                f"ERROR: {path} appears to be a binary file. "
                "Do not read binary assets (png/jpg/pdf) as text. "
                "If visual inspection is required, upload the file and reference its file_id."
            )
        return file_path.read_text(encoding="utf-8")

    @function_tool
    def replace_in_file(path: str, old_text: str, new_text: str, replace_all: bool = False) -> str:
        """Replace text in a workspace file. Errors if old_text is not found."""
        if not old_text:
            return "ERROR: old_text must be non-empty"
        file_path = safe_path(path)
        if not file_path.exists() or not file_path.is_file():
            return f"ERROR: {path} does not exist"
        if not _is_probably_text(file_path):
            return f"ERROR: {path} is not a text file"

        original = file_path.read_text(encoding="utf-8")
        if old_text not in original:
            return f"ERROR: old_text not found in {path}"

        count = original.count(old_text)
        if replace_all:
            updated = original.replace(old_text, new_text)
            replaced = count
        else:
            updated = original.replace(old_text, new_text, 1)
            replaced = 1

        file_path.write_text(updated, encoding="utf-8")
        return f"Replaced {replaced} occurrence(s) in {path}"

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
    def run_python(script_path: str, timeout: int = 10) -> str:
        """
        Execute a Python script from the workspace and return a structured text report.

        Args:
            script_path: Relative path to the Python file inside the workspace.
                Absolute paths and paths escaping the workspace are rejected by `safe_path`.
            timeout: Max execution time in seconds for `subprocess.run`.

        Behavior:
            - If `script_path` does not exist, returns an `ERROR:` message and lists
              available `.py` files in the workspace when possible.
            - If `script_path` exists but is not a file, returns an `ERROR:` message.
            - If execution succeeds or fails, always returns:
              `exit_code=<int>`, followed by stdout and stderr sections.

        Returns:
            A plain-text string intended for LLM consumption, either an `ERROR:` message
            or an execution report with `exit_code`, `--- STDOUT ---`, and
            `--- STDERR ---` blocks.
        """
        file_path = safe_path(script_path)
        if not file_path.exists():
            available = sorted(str(p.relative_to(workspace)) for p in workspace.rglob("*.py"))
            if not available:
                return (
                    f"ERROR: {script_path} does not exist\n"
                    "No Python files found in workspace. Create one with write_file first."
                )
            return (
                f"ERROR: {script_path} does not exist\n"
                "Available Python files:\n"
                + "\n".join(f"- {item}" for item in available)
            )
        if not file_path.is_file():
            return f"ERROR: {script_path} is not a file"

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
        """Read one shared skill by skill directory name (or legacy .md filename)."""
        try:
            return read_shared_skill(skill_name)
        except FileNotFoundError as exc:
            return f"Skill not found: {exc}"

    additional_instructions = load_agent_notes()
    code_agent = Agent(
        name="code_assistant",
        instructions=build_code_executor_instructions(additional_instructions, task_type=task_type),
        model="gpt-5.4-mini",
        tools=[
            write_file, read_file, replace_in_file, list_files,
            run_python,
            get_database_schema,
            get_unique_values,
            get_column_stats,
            preview_table,
            search_agent_skills,
            read_agent_skill,
        ],
        output_type=CodeAgentResult,
    )
    return code_agent
