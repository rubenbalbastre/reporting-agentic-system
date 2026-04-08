from agents import function_tool, Agent
from pathlib import Path


# Base directory for reports
REPORTS_DIR = Path("workspace/")
REPORTS_DIR.mkdir(exist_ok=True)


def _get_report_path(report_id: str) -> Path:
    """Resolve report_id to a markdown file path."""
    safe_id = report_id.replace(" ", "_").lower()
    return REPORTS_DIR / f"{safe_id}" / "report.md"


def build_report_agent(report_id: str) -> Agent:

    @function_tool
    def create_report(content: str) -> str:
        """
        Create or overwrite a report with full markdown content.
        """
        path = _get_report_path(report_id)
        path.write_text(content, encoding="utf-8")
        return f"Report '{report_id}' saved at {path}"


    @function_tool
    def get_report() -> str:
        """
        Retrieve the full markdown content of a report.
        """
        path = _get_report_path(report_id)
        if not path.exists():
            raise FileNotFoundError(f"Report '{report_id}' does not exist.")
        return path.read_text(encoding="utf-8")


    @function_tool
    def update_report_section(heading: str, content: str) -> str:
        """
        Replace or create a section in the markdown report.

        heading must match exactly (e.g., "## Results").
        """
        path = _get_report_path(report_id)

        if not path.exists():
            raise FileNotFoundError(f"Report '{report_id}' does not exist.")

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
        name="Report agent",
        instructions=(
            "You are a helpful assistant which helps users to generate reports based on their questions."
            "To do that, you can create a new report, update specific sections of the report, or retrieve the full report content."
            "Use the provided tools to manage the report content in markdown format."
        ),
        model="gpt-5.4-nano",
        tools=[create_report, get_report, update_report_section],
    )