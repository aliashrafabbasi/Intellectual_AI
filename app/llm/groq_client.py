from collections.abc import Iterator

from groq import Groq

from app.core.config import (
    GROQ_API_KEY,
    GROQ_CHAT_TEMPERATURE,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_ON_DEMAND_TOKEN_BUDGET,
    GROQ_TITLE_MAX_TOKENS,
    GROQ_TITLE_MODEL,
)

_client = Groq(api_key=GROQ_API_KEY)

# Slack between our char-based estimate and Groq’s real tokenizer (avoids 413).
_TOKEN_BUDGET_SLACK = 200


def _estimate_prompt_tokens(messages: list) -> int:
    """Pessimistic input-token estimate: prompt + max_tokens must stay under on_demand TPM."""
    if not messages:
        return 1
    total = 0
    for m in messages:
        c = str(m.get("content", ""))
        total += max(1, (len(c) + 2) // 3)
    total += max(4, len(messages) * 4)
    # Char/3 often underestimates vs BPE; bias high so we shrink max_tokens enough.
    return int(total * 1.12) + 32


def _completion_max_tokens(messages: list) -> int:
    """
    Groq on_demand rejects when estimated prompt + requested max_tokens exceeds ~6000 TPM.
    """
    prompt_est = _estimate_prompt_tokens(messages)
    room = GROQ_ON_DEMAND_TOKEN_BUDGET - prompt_est - _TOKEN_BUDGET_SLACK
    # Never pass negative max_tokens to the API.
    capped = min(GROQ_MAX_TOKENS, max(0, room))
    return max(16, capped)

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
        model=GROQ_TITLE_MODEL,
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
        temperature=GROQ_CHAT_TEMPERATURE,
        max_tokens=_completion_max_tokens(messages),
    )
    return (completion.choices[0].message.content or "").strip()


def stream_ai_response(messages: list) -> Iterator[str]:
    stream = _client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=GROQ_CHAT_TEMPERATURE,
        max_tokens=_completion_max_tokens(messages),
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and getattr(delta, "content", None):
            yield delta.content
