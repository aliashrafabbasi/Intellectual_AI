from collections.abc import Iterator

from groq import Groq

from app.core.config import (
    GROQ_API_KEY,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_TITLE_MAX_TOKENS,
)

_client = Groq(api_key=GROQ_API_KEY)

_TITLE_SYSTEM = (
    "You reply with ONLY a short conversation title (maximum 8 words). "
    "Capture the main topic from the exchange. "
    "Plain text: no quotation marks, no emoji, no trailing period."
)


def _sanitize_title(raw: str) -> str:
    s = " ".join((raw or "").replace("\n", " ").split()).strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    if len(s) > 120:
        s = s[:117].rstrip() + "…"
    return s


def generate_chat_title(user_message: str, assistant_reply: str) -> str:
    """One cheap Groq call to label a chat from the first user + assistant messages."""
    u = (user_message or "")[:1500]
    a = (assistant_reply or "")[:1500]
    completion = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": _TITLE_SYSTEM},
            {
                "role": "user",
                "content": f"User:\n{u}\n\nAssistant:\n{a}",
            },
        ],
        temperature=0.25,
        max_tokens=min(GROQ_TITLE_MAX_TOKENS, 128),
    )
    return _sanitize_title(completion.choices[0].message.content or "")


def get_ai_response(messages: list) -> str:
    completion = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=GROQ_MAX_TOKENS,
    )
    return (completion.choices[0].message.content or "").strip()


def stream_ai_response(messages: list) -> Iterator[str]:
    stream = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.4,
        max_tokens=GROQ_MAX_TOKENS,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and getattr(delta, "content", None):
            yield delta.content
