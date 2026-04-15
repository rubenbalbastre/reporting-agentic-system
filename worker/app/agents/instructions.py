from pathlib import Path


def load_agent_notes() -> str:
    """
    Load optional markdown instructions from app/agent_notes.md.
    Returns empty string if the file does not exist.
    """
    notes_path = Path(__file__).resolve().parent / "agent_notes.md"
    if not notes_path.exists():
        return ""
    return notes_path.read_text(encoding="utf-8").strip()
