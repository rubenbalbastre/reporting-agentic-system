from agents import function_tool, Agent
from pathlib import Path
from app.workspace_paths import (
    get_report_workspace,
    get_report_markdown_path,
    resolve_workspace_relative_path,
)


def build_report_agent(report_id: int) -> Agent:
    workspace = get_report_workspace(report_id)

    def safe_path(rel_path: str) -> Path:
        return resolve_workspace_relative_path(workspace, rel_path)

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
    def read_report() -> str:
        """
        Retrieve the full markdown content of a report.
        """
        path = get_report_markdown_path(report_id)
        return path.read_text(encoding="utf-8")


    @function_tool
    def update_report_section(heading: str, content: str) -> str:
        """
        Replace or create a section in the markdown report.

        heading must match exactly (e.g., "## Results").
        """
        path = get_report_markdown_path(report_id)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        new_lines = []
        in_target_section = False
        section_found = False

        for i, line in enumerate(lines):
            if line.strip() == heading:
                # Start replacing this section
                section_found = True
                in_target_section = True
                new_lines.append(heading)
                new_lines.append(content)
                continue

            # Detect next section (another heading)
            if in_target_section and line.startswith("#"):
                in_target_section = False

            if not in_target_section:
                new_lines.append(line)

        # If section not found → append it
        if not section_found:
            new_lines.append("")  # spacing
            new_lines.append(heading)
            new_lines.append(content)

        updated_text = "\n".join(new_lines) + "\n"
        path.write_text(updated_text, encoding="utf-8")

        return f"Section '{heading}' updated in report '{report_id}'"

    return Agent(
        name="report_agent",
        instructions=(
            "You must update a markdown report based on the user's question and results from the artifact worker, which you can find in the workspace using list_files and read_file tools."
            "Use the provided tools to manage the report content in markdown format."
            f"When referencing images generated in this report workspace, use markdown image syntax with backend file URLs in this exact format: ![alt text](/reports/{report_id}/files/<filename>)."
        ),
        model="gpt-5.4-nano",
        tools=[read_report, update_report_section, list_files, read_file],
    )
