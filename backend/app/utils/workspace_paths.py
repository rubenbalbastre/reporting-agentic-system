import os
from pathlib import Path


def get_report_workspace(report_id: int) -> Path:
    """Return the persistent workspace directory for one report, creating it if needed."""
    workspace_root = Path(os.getenv("WORKSPACE_ROOT", "/data/shared/jobs"))
    workspace = (workspace_root / f"report_{report_id}").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def get_report_markdown_path(report_id: int) -> Path:
    """Return the canonical `report.md` path for one report workspace."""
    return get_report_workspace(report_id) / "report.md"


def resolve_workspace_relative_path(workspace: Path, rel_path: str) -> Path:
    """Resolve a relative path inside a workspace and reject path traversal."""
    raw = Path(rel_path)
    if raw.is_absolute():
        raise ValueError("Path must be relative to workspace")

    candidate = (workspace / raw).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("Path escapes workspace") from exc
    return candidate
