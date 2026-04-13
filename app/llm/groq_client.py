from collections.abc import Iterator

from groq import Groq

from app.core.config import GROQ_API_KEY, GROQ_MAX_TOKENS, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)


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
