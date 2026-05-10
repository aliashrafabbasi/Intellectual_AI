import os

from dotenv import load_dotenv

load_dotenv()

# Supports MONGO_URI or legacy MONGO_URL; defaults to local MongoDB.
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGO_URL") or "mongodb://127.0.0.1:27017"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Lower latency: llama-3.1-8b-instant. For higher quality use e.g. llama-3.3-70b-versatile or openai/gpt-oss-120b
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
# Title generation uses this model by default so auto-naming stays fast even if GROQ_MODEL is large/slow.
GROQ_TITLE_MODEL = os.getenv("GROQ_TITLE_MODEL", "llama-3.1-8b-instant")
# Max completion tokens per request. Keep moderate: Groq on_demand TPM (~6000) counts
# prompt + max_tokens together — a large max_tokens + long prompt causes 413.
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
# Hard ceiling for (estimated_prompt + max_tokens) on free/on_demand tiers (see groq_client).
GROQ_ON_DEMAND_TOKEN_BUDGET = int(os.getenv("GROQ_ON_DEMAND_TOKEN_BUDGET", "5900"))
# Short titles for auto-naming chats (cheap completion)
GROQ_TITLE_MAX_TOKENS = int(os.getenv("GROQ_TITLE_MAX_TOKENS", "96"))
# Main chat completion — slightly lower = snappier sampling on average (env override).
GROQ_CHAT_TEMPERATURE = float(os.getenv("GROQ_CHAT_TEMPERATURE", "0.35"))
# Only the last N prior messages are loaded from Mongo before budget trimming.
CHAT_CONTEXT_MESSAGES = max(4, int(os.getenv("CHAT_CONTEXT_MESSAGES", "16")))
# Target max *estimated* tokens for the full prompt (system + history + user). Groq on_demand
# rejects around 6000 real tokens — we stay well under because char-based estimates are loose.
GROQ_MAX_PROMPT_TOKENS_ESTIMATE = max(1500, int(os.getenv("GROQ_MAX_PROMPT_TOKENS_ESTIMATE", "4800")))
# Hard cap per message body (characters) before sending to Groq (large pastes / code dumps).
CHAT_MESSAGE_MAX_CHARS = max(2000, int(os.getenv("CHAT_MESSAGE_MAX_CHARS", "8000")))
# Extra safety: max combined characters for all non-system messages (history + current user).
CHAT_MAX_REST_CHARS = max(4000, int(os.getenv("CHAT_MAX_REST_CHARS", "14000")))

CHAT_MEMORY_DAYS = 7

# Comma-separated browser origins allowed to call the API (React dev server, production host).
_default_cors = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
CORS_ORIGINS = [
    o.strip()
    for o in (os.getenv("CORS_ORIGINS") or _default_cors).split(",")
    if o.strip()
]
