from agents import function_tool, Agent
import mimetypes
import re
from pathlib import Path
from openai import OpenAI
from app.utils.workspace_paths import (
    get_report_workspace,
    get_report_markdown_path,
    resolve_workspace_relative_path,
)
from app.agents.prompts import build_report_agent_instructions


def build_report_agent(report_id: int) -> Agent:
    workspace = get_report_workspace(report_id)
    report_files_prefixes = (f"/reports/{report_id}/files/", f"/reports/{report_id}/")
    image_ref_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
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

    def safe_path(rel_path: str) -> Path:
        return resolve_workspace_relative_path(workspace, rel_path)

    def _resolve_report_image_src(src: str) -> Path | None:
        raw_src = (src or "").strip().strip("<>").strip()
        if not raw_src or raw_src.startswith(("http://", "https://", "data:", "blob:")):
            return None

        rel: str | None = None
        for prefix in report_files_prefixes:
            if raw_src.startswith(prefix):
                rel = raw_src[len(prefix):]
                break
        if rel is None and not raw_src.startswith("/"):
            rel = raw_src.replace("./", "", 1)

        if not rel:
            return None
        try:
            file_path = safe_path(rel)
        except Exception:
            return None
        if not file_path.exists() or not file_path.is_file():
            return None
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type or not mime_type.startswith("image/"):
            return None
        return file_path

    def _upload_image_for_reasoning(file_path: Path, display_path: str | None = None) -> str:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        with file_path.open("rb") as fh:
            uploaded = client.files.create(file=fh, purpose="assistants")
        label = display_path or str(file_path.relative_to(workspace))
        return f"path={label} file_id={uploaded.id} mime={mime_type or 'application/octet-stream'}"

    def _strip_html_comments(text: str) -> str:
        # Keep report markdown clean: remove hidden anchors like <!-- ... -->
        return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

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
        markdown_text = path.read_text(encoding="utf-8")
        image_upload_notes: list[str] = []
        seen: set[Path] = set()

        for match in image_ref_pattern.finditer(markdown_text):
            image_path = _resolve_report_image_src(match.group(1))
            if not image_path or image_path in seen:
                continue
            seen.add(image_path)
            try:
                image_upload_notes.append(_upload_image_for_reasoning(image_path))
            except Exception as exc:
                image_upload_notes.append(f"path={image_path.relative_to(workspace)} upload_error={exc}")

        if not image_upload_notes:
            return markdown_text
        return (
            markdown_text
            + "\n\n<!-- REPORT_IMAGE_FILES_FOR_REASONING\n"
            + "\n".join(image_upload_notes)
            + "\n-->"
        )
    
    @function_tool
    def update_report_section(heading: str, content: str) -> str:
        """
        Replace or create a section in the markdown report. Use only top-level or second-level headings (e.g., "# Summary" or "## Results") to identify sections. The

        heading must match exactly (e.g., "## Results").
        """
        path = get_report_markdown_path(report_id)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        match = re.match(r"^(#{1,6})\s*(.+?)\s*$", heading.strip())
        if not match:
            return "ERROR: heading must be markdown heading format like '# Title' or '## Title'"
        target_marks = match.group(1)
        target_title = match.group(2).strip()
        target_norm = target_title.lower()
        canonical_heading = f"{target_marks} {target_title}"
        sanitized_content = _strip_html_comments(content).strip()

        # Capture markdown heading sections as [start, end) ranges.
        sections: list[tuple[int, int, str, str]] = []
        for idx, line in enumerate(lines):
            h = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if not h:
                continue
            sections.append((idx, len(target_marks), h.group(2).strip(), line))

        ranges: list[tuple[int, int]] = []
        for i, (start, _level, title, _raw) in enumerate(sections):
            title_norm = title.lower()
            if title_norm != target_norm:
                continue
            end = sections[i + 1][0] if i + 1 < len(sections) else len(lines)
            ranges.append((start, end))

        if not ranges:
            new_lines = list(lines)
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            new_lines.append(canonical_heading)
            new_lines.append(sanitized_content)
            updated_text = "\n".join(new_lines).rstrip() + "\n"
            updated_text = _strip_html_comments(updated_text).rstrip() + "\n"
            path.write_text(updated_text, encoding="utf-8")
            return f"Section '{canonical_heading}' created in report '{report_id}'"

        first_start, first_end = ranges[0]
        skip_ranges = ranges[1:]
        new_lines: list[str] = []
        idx = 0
        while idx < len(lines):
            # Replace first matched section once.
            if idx == first_start:
                new_lines.append(canonical_heading)
                new_lines.append(sanitized_content)
                idx = first_end
                continue
            # Drop duplicate matching sections.
            skipped = False
            for s, e in skip_ranges:
                if idx == s:
                    idx = e
                    skipped = True
                    break
            if skipped:
                continue
            new_lines.append(lines[idx])
            idx += 1

        updated_text = _strip_html_comments("\n".join(new_lines)).rstrip() + "\n"
        path.write_text(updated_text, encoding="utf-8")
        removed = max(0, len(ranges) - 1)
        return (
            f"Section '{canonical_heading}' updated in report '{report_id}'. "
            f"Removed {removed} duplicate section(s)."
        )

    return Agent(
        name="report_agent",
        instructions=build_report_agent_instructions(report_id),
        model="gpt-5.4-nano",
        tools=[read_report, list_files, read_file, update_report_section],
    )
