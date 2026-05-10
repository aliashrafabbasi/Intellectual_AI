import threading
from collections.abc import Iterator

from app.core.config import (
    CHAT_CONTEXT_MESSAGES,
    CHAT_MAX_REST_CHARS,
    CHAT_MESSAGE_MAX_CHARS,
    GROQ_MAX_PROMPT_TOKENS_ESTIMATE,
)
from app.db.repositories import (
    add_message_pair,
    create_chat,
    delete_chat_by_session,
    ensure_chat,
    get_chat_document,
    get_chat_messages_tail,
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


def _estimate_tokens(text: str) -> int:
    """
    Conservative token estimate for trimming (Groq's real count is often higher than len/4 for code).
    """
    if not text:
        return 0
    # ~3 chars per token upper bound for mixed text/code; matches Groq limits better than //4.
    return max(1, (len(text) + 2) // 3)


def _truncate_message_body(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _trim_messages_for_groq_limits(messages: list) -> list:
    """
    Groq on-demand tier rejects prompts over ~6000 tokens (413 / TPM).
    Drop oldest history first; never delete the final message (current user turn) — only shorten it.
    """
    if not messages:
        return messages
    system = messages[0]
    rest = messages[1:]
    rest = [
        {"role": m["role"], "content": _truncate_message_body(str(m.get("content", "")), CHAT_MESSAGE_MAX_CHARS)}
        for m in rest
    ]
    if not rest:
        return [system]

    sys_est = _estimate_tokens(str(system.get("content", "")))
    budget = GROQ_MAX_PROMPT_TOKENS_ESTIMATE - sys_est
    budget = max(400, budget)

    # Last item is always the new user message from _build_messages.
    current = rest[-1]
    prior = rest[:-1]

    def over(parts: list) -> bool:
        if not parts:
            return False
        tok = sum(_estimate_tokens(m["content"]) for m in parts)
        chars = sum(len(m["content"]) for m in parts)
        return tok > budget or chars > CHAT_MAX_REST_CHARS

    while prior and over(prior + [current]):
        if len(prior) >= 2:
            prior = prior[2:]
        else:
            prior = []

    combined = prior + [current]
    while over(combined):
        content = combined[-1]["content"]
        if len(content) <= 800:
            break
        step = max(800, len(content) // 2)
        combined[-1] = {
            **combined[-1],
            "content": _truncate_message_body(content, step),
        }

    return [system] + combined


def ensure_session_document(session_id: str) -> dict:
    """Expose ensure_chat for the API (empty session appears in list before first message)."""
    return ensure_chat(session_id)


def _defer_maybe_auto_title(session_id: str) -> None:
    """Run title LLM off the hot path so streams close immediately after the reply."""

    def run() -> None:
        try:
            maybe_auto_title_session(session_id)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


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
    prior = get_chat_messages_tail(session_id, CHAT_CONTEXT_MESSAGES)
    if prior is None:
        create_chat(session_id)
        prior = []

    messages: list = [{"role": "system", "content": INTELLECTUAL_PROMPT}]
    for msg in prior:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return _trim_messages_for_groq_limits(messages)


def chat_with_ai(session_id: str, user_message: str) -> str:
    messages = _build_messages(session_id, user_message)
    ai_response = get_ai_response(messages)
    add_message_pair(session_id, user_message, ai_response)
    _defer_maybe_auto_title(session_id)
    return ai_response


def stream_chat_with_ai(session_id: str, user_message: str) -> Iterator[str]:
    messages = _build_messages(session_id, user_message)
    parts: list[str] = []
    for chunk in stream_ai_response(messages):
        parts.append(chunk)
        yield chunk
    add_message_pair(session_id, user_message, "".join(parts))
    _defer_maybe_auto_title(session_id)


def list_chats():
    return list_chat_summaries()


def load_chat(session_id: str) -> dict | None:
    return get_chat_document(session_id)


def remove_chat(session_id: str):
    return delete_chat_by_session(session_id)


def rename_session(session_id: str, name: str) -> dict:
    return update_session_name(session_id, name.strip())
