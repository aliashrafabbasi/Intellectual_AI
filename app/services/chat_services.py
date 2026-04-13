from collections.abc import Iterator

from app.db.repositories import (
    add_message_pair,
    create_chat,
    delete_chat_by_session,
    get_all_chats,
    get_chat,
    update_session_name,
)
from app.llm.groq_client import get_ai_response, stream_ai_response
from app.llm.prompts import INTELLECTUAL_PROMPT


def _build_messages(session_id: str, user_message: str) -> list:
    chat = get_chat(session_id)
    if not chat:
        chat = create_chat(session_id)

    messages: list = [{"role": "system", "content": INTELLECTUAL_PROMPT}]
    for msg in chat.get("messages") or []:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


def chat_with_ai(session_id: str, user_message: str) -> str:
    messages = _build_messages(session_id, user_message)
    ai_response = get_ai_response(messages)
    add_message_pair(session_id, user_message, ai_response)
    return ai_response


def stream_chat_with_ai(session_id: str, user_message: str) -> Iterator[str]:
    messages = _build_messages(session_id, user_message)
    parts: list[str] = []
    for chunk in stream_ai_response(messages):
        parts.append(chunk)
        yield chunk
    add_message_pair(session_id, user_message, "".join(parts))


def list_chats():
    return get_all_chats()


def remove_chat(session_id: str):
    return delete_chat_by_session(session_id)


def rename_session(session_id: str, name: str) -> dict:
    return update_session_name(session_id, name.strip())
