from typing import Any


def build_chat_input(prefix: str, history_rows: list[dict[str, Any]], user_content: str, max_messages: int = 20) -> str:
    recent = history_rows[-max_messages:]
    lines = [f"{row['role']}: {row['content']}" for row in recent]
    lines.append(f"user: {user_content}")
    return f"{prefix}\n" + "\n".join(lines)
