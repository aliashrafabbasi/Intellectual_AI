import os

from dotenv import load_dotenv

load_dotenv()

# Supports MONGO_URI or legacy MONGO_URL; defaults to local MongoDB.
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGO_URL") or "mongodb://127.0.0.1:27017"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Lower latency: llama-3.1-8b-instant. For higher quality use e.g. llama-3.3-70b-versatile or openai/gpt-oss-120b
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "4096"))

CHAT_MEMORY_DAYS = 7