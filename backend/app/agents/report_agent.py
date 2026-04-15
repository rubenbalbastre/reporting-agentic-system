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
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
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

    def _to_report_file_url(src: str) -> str:
        raw_src = (src or "").strip().strip("<>").strip()
        if not raw_src:
            return raw_src
        if raw_src.startswith(("http://", "https://", "data:", "blob:")):
            return raw_src

        if raw_src.startswith(f"/reports/{report_id}/files/"):
            return raw_src
        if raw_src.startswith(f"/reports/{report_id}/"):
            rel = raw_src[len(f"/reports/{report_id}/"):]
            return f"/reports/{report_id}/files/{rel}"

        rel = raw_src.replace("./", "", 1).lstrip("/")
        if not rel:
            return raw_src
        return f"/reports/{report_id}/files/{rel}"

    def _normalize_markdown_image_paths(text: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            alt = match.group(1)
            src = match.group(2)
            normalized = _to_report_file_url(src)
            return f"![{alt}]({normalized})"

        return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _replace, text)

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
    def build_report_file_url(relative_path: str) -> str:
        """
        Build a canonical backend URL for a workspace file:
        /reports/{report_id}/files/<relative_path>
        """
        rel = (relative_path or "").strip().replace("./", "", 1).lstrip("/")
        if not rel:
            return "ERROR: relative_path is required"
        try:
            file_path = safe_path(rel)
        except Exception:
            return "ERROR: invalid path; it must stay inside the report workspace"
        if not file_path.exists() or not file_path.is_file():
            return f"ERROR: {rel} does not exist in report workspace"
        return f"/reports/{report_id}/files/{rel}"

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
    def update_report(content: str) -> str:
        """
        Rewrite the full markdown report content.
        """
        path = get_report_markdown_path(report_id)
        sanitized = _strip_html_comments(content or "").rstrip()
        sanitized = _normalize_markdown_image_paths(sanitized)
        if not sanitized:
            return "ERROR: content is required"
        path.write_text(sanitized + "\n", encoding="utf-8")
        return "Report updated"

    @function_tool
    def update_report_section(heading: str, content: str) -> str:
        """
        Replace or create a single section in the markdown report.
        Provide `heading` (e.g., "## Insights") and `content`.
        """
        if not (heading or "").strip():
            return "ERROR: heading is required. Use update_report to rewrite the full report."
        m = re.match(r"^(#{1,6})\s*(.+?)\s*$", heading.strip())
        if not m:
            return "ERROR: heading must be markdown heading format like '# Title' or '## Title'"

        path = get_report_markdown_path(report_id)
        lines = path.read_text(encoding="utf-8").splitlines()
        canonical_heading = f"{m.group(1)} {m.group(2).strip()}"
        target_key = canonical_heading.lower()
        section_body = _normalize_markdown_image_paths(_strip_html_comments(content or "").strip())

        sections: list[tuple[int, int]] = []
        for i, line in enumerate(lines):
            h = heading_pattern.match(line.strip())
            if not h:
                continue
            key = f"{h.group(1)} {h.group(2).strip()}".lower()
            if key != target_key:
                continue
            # Capture the full section span: heading line until the next heading (or EOF).
            end = i + 1
            while end < len(lines) and not heading_pattern.match(lines[end].strip()):
                end += 1
            sections.append((i, end))

        if not sections:
            # If the section does not exist, append it at the end of the report.
            if lines and lines[-1].strip():
                lines.append("")
            lines.extend([canonical_heading, section_body])
            path.write_text(_strip_html_comments("\n".join(lines)).rstrip() + "\n", encoding="utf-8")
            return f"Section '{canonical_heading}' created"

        first_start, first_end = sections[0]
        new_lines: list[str] = []
        i = 0
        while i < len(lines):
            if i == first_start:
                # Replace only the first matching section with the new content.
                new_lines.extend([canonical_heading, section_body])
                i = first_end
                continue
            duplicate = next((end for start, end in sections[1:] if i == start), None)
            if duplicate is not None:
                # Drop additional duplicate sections with the same heading.
                i = duplicate
                continue
            new_lines.append(lines[i])
            i += 1

        path.write_text(_strip_html_comments("\n".join(new_lines)).rstrip() + "\n", encoding="utf-8")
        removed = max(0, len(sections) - 1)
        return f"Section '{canonical_heading}' updated. Removed {removed} duplicate(s)."

    return Agent(
        name="report_agent",
        instructions=build_report_agent_instructions(report_id),
        model="gpt-5.4-mini",
        tools=[
            read_report,
            list_files,
            read_file,
            replace_in_file,
            build_report_file_url,
            update_report,
            update_report_section,
        ],
    )
