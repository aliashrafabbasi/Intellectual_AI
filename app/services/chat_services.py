from collections.abc import Iterator

from app.db.repositories import (
    add_message_pair,
    create_chat,
    delete_chat_by_session,
    ensure_chat,
    get_chat_document,
    list_chat_summaries,
    get_chat,
    update_session_name,
)
from app.llm.groq_client import generate_chat_title, get_ai_response, stream_ai_response
from app.llm.prompts import INTELLECTUAL_PROMPT


def _is_placeholder_chat_name(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n:
        return True
    return n in (
        "untitled chat",
        "untitled",
        "new session",
        "new chat",
        "untilled chat",
        "untilled",
    )


def _fallback_title_from_user(user_message: str, max_len: int = 52) -> str:
    s = " ".join((user_message or "").replace("\n", " ").split()).strip()
    if not s:
        return ""
    if len(s) > max_len:
        return s[: max_len - 1].rstrip() + "…"
    return s


def ensure_session_document(session_id: str) -> dict:
    """Expose ensure_chat for the API (empty session appears in list before first message)."""
    return ensure_chat(session_id)


def maybe_auto_title_session(session_id: str) -> None:
    """After messages are saved: if name is still default, set title from first exchange."""
    chat = get_chat(session_id)
    if not chat:
        return
    if not _is_placeholder_chat_name((chat.get("name") or "").strip()):
        return
    msgs = chat.get("messages") or []
    first_user: str | None = None
    first_asst: str | None = None
    for m in msgs:
        if not isinstance(m, dict):
            continue
        role, content = m.get("role"), str(m.get("content") or "")
        if role == "user" and first_user is None:
            first_user = content
        elif role == "assistant" and first_user is not None and first_asst is None:
            first_asst = content
            break
    if not first_user or not first_asst:
        return
    title = ""
    try:
        title = (generate_chat_title(first_user, first_asst) or "").strip()
    except Exception:
        title = ""
    if not title:
        title = _fallback_title_from_user(first_user)
    if title:
        update_session_name(session_id, title)


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
    maybe_auto_title_session(session_id)
    return ai_response


def stream_chat_with_ai(session_id: str, user_message: str) -> Iterator[str]:
    messages = _build_messages(session_id, user_message)
    parts: list[str] = []
    for chunk in stream_ai_response(messages):
        parts.append(chunk)
        yield chunk
    add_message_pair(session_id, user_message, "".join(parts))
    maybe_auto_title_session(session_id)


def list_chats():
    return list_chat_summaries()


def load_chat(session_id: str) -> dict | None:
    return get_chat_document(session_id)


def remove_chat(session_id: str):
    return delete_chat_by_session(session_id)


def rename_session(session_id: str, name: str) -> dict:
    return update_session_name(session_id, name.strip())
