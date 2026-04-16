from typing import Any


def build_chat_input(
    prefix: str, history_rows: list[dict[str, Any]], user_content: str, max_messages: int = 20
) -> list[dict[str, str]]:
    recent = history_rows[-max_messages:]
    messages: list[dict[str, str]] = [{"role": "system", "content": prefix}]
    messages.extend(
        {
            "role": str(row.get("role", "user")),
            "content": str(row.get("content", "")),
        }
        for row in recent
    )
    messages.append({"role": "user", "content": user_content})
    return messages
