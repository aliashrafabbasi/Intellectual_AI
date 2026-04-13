# Intellectual AI Chat

A **local full-stack chatbot**: a **FastAPI** backend streams answers from **Groq** (Llama-class models), **MongoDB** stores conversations, and a **Streamlit** web app provides a ChatGPT-style interface with session history, search, and rename/delete controls.

The assistant persona is **“Jeffry the Genius”**—an intellectual, reasoning-focused helper (see `app/llm/prompts.py`). It defaults to **Roman Urdu** when you write in Urdu or Roman Urdu, and otherwise follows the user’s language.

---

## What’s in the box

| Layer | Role |
|--------|------|
| **FastAPI** (`main.py`) | REST API under `/api/v1`: streaming chat, list/rename/delete sessions. |
| **Groq** (`groq` SDK) | LLM inference; model configurable via `.env`. |
| **MongoDB** (`pymongo`) | Persistent chats: `session_id`, messages, titles, timestamps. |
| **Streamlit** (`streamlit_app.py`) | Browser UI: streaming replies, sidebar conversations, search, connection status. |

You run **two processes**: the API (Uvicorn) and the UI (Streamlit). The UI calls the API using `INTELLECTUAL_API_URL` from `.env`.

---

## Tech stack

- **Language:** Python 3.11+ (3.12 tested)
- **Web API:** [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- **Validation:** [Pydantic](https://docs.pydantic.dev/) v2
- **LLM:** [Groq](https://groq.com/) API via the official [`groq`](https://pypi.org/project/groq/) client
- **Database:** [MongoDB](https://www.mongodb.com/) via [PyMongo](https://www.mongodb.com/docs/drivers/python/)
- **Frontend:** [Streamlit](https://streamlit.io/)
- **HTTP (UI → API):** [HTTPX](https://www.python-httpx.org/), [Requests](https://requests.readthedocs.io/)
- **Config:** [python-dotenv](https://pypi.org/project/python-dotenv/) (`.env` loaded in `main.py`, `app/core/config.py`, and `streamlit_app.py`)

---

## Prerequisites

1. **Python 3.11+**
2. **MongoDB** reachable at the URL you put in `.env` (local install, cloud URI, or Docker)
3. A **Groq API key** from the [Groq Console](https://console.groq.com/)

---

## Installation

From the project root:

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

That single command installs all Python dependencies for both the API and the Streamlit app.

---

## Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit **`.env`** (never commit it; it is in `.gitignore`):

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `GROQ_API_KEY` | **Yes** | Groq API key. |
   | `MONGO_URI` | No* | MongoDB connection string. Default: `mongodb://127.0.0.1:27017`. *Required in practice if you don’t run Mongo locally. |
   | `GROQ_MODEL` | No | Model id (default: `llama-3.1-8b-instant`). |
   | `GROQ_MAX_TOKENS` | No | Max tokens (default: `4096`). |
   | `INTELLECTUAL_API_URL` | No | Base URL of the FastAPI app for Streamlit (default: `http://127.0.0.1:8000`). |

   Legacy alias: `MONGO_URL` is still read if `MONGO_URI` is unset.

---

## Running the app

You need **MongoDB running** before chats can be saved (and the sidebar list works).

### Optional: MongoDB with Docker

```bash
docker run -d --name intellectual-mongo -p 27017:27017 mongo:7
```

Match `MONGO_URI` in `.env` to that host (e.g. `mongodb://127.0.0.1:27017`).

### Terminal 1 — API

```bash
source venv/bin/activate
uvicorn main:app --reload
```

- API base: `http://127.0.0.1:8000`
- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Terminal 2 — Streamlit UI

```bash
source venv/bin/activate
streamlit run streamlit_app.py
```

Open the URL Streamlit prints (typically **http://localhost:8501**). Ensure `INTELLECTUAL_API_URL` in `.env` points at the same host/port as Uvicorn.

### Docker (full stack)

1. Copy and edit environment variables:

   ```bash
   cp .env.example .env
   ```

   Set **`GROQ_API_KEY`** (required). Compose overrides `MONGO_URI` and `INTELLECTUAL_API_URL` for container networking; optional keys such as `GROQ_MODEL` still apply when present in `.env`.

2. Start MongoDB, the API, and Streamlit:

   ```bash
   docker compose up --build
   ```

3. Open the UI at **[http://localhost:8501](http://localhost:8501)** and API docs at **[http://localhost:8000/docs](http://localhost:8000/docs)**. MongoDB is **not** published on the host (only reachable as `mongo` inside Compose), which avoids conflicts if you already run MongoDB on port 27017. To open a shell: `docker compose exec mongo mongosh`.

---

## API overview (prefix `/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat/stream` | Stream assistant reply (`session_id`, `message` in JSON body). |
| `POST` | `/chat` | Non-streaming chat (query params `session_id`, `message`). |
| `GET` | `/chats` | List stored chats. |
| `PATCH` | `/chat/{session_id}` | Rename a session (`name` in JSON body). |
| `DELETE` | `/chat/{session_id}` | Delete a session. |

The Streamlit client uses the streaming endpoint for lower perceived latency.

---

## Project layout

```
Intellectual_AI_Chat/
├── main.py                 # FastAPI entry, loads .env
├── streamlit_app.py        # Streamlit UI
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image (API default CMD)
├── docker-compose.yml      # Mongo + API + Streamlit
├── .env.example            # Template for secrets (copy to .env)
├── app/
│   ├── api/v1/chat.py      # Chat routes
│   ├── core/config.py      # Settings from environment
│   ├── db/mongo.py         # Mongo client
│   ├── db/repositories.py  # Chat CRUD
│   ├── llm/groq_client.py  # Groq chat + stream
│   ├── llm/prompts.py      # System prompt / persona
│   └── services/chat_services.py
├── assets/                 # Chat avatars (user / AI)
└── .streamlit/config.toml  # Streamlit theme defaults
```

---

## Troubleshooting

- **Docker build fails with `network is unreachable` / IPv6 (`dial tcp [...]:443`)** — The daemon is pulling `python:3.12-slim` over a path that uses IPv6, but this machine has no working IPv6 route. Try: **Docker Desktop** → Settings → Resources → Network → adjust options or reset; or on Linux, make the system prefer IPv4 for name resolution (e.g. in `/etc/gai.conf`, uncomment the line `precedence ::ffff:0:0/96  100`); or fix/disable broken IPv6 routing. Then run `docker pull python:3.12-slim` and `docker compose build` again.
- **`Bind for 0.0.0.0:27017 failed: port is already allocated`** — Something else is using host port 27017 (often a system MongoDB or another container). The Compose file does **not** map Mongo to the host; if you still see this, you may be on an old `docker-compose.yml`—pull the latest—or stop the other process (`docker ps`, or `sudo ss -tlnp | grep 27017`).
- **`ServerSelectionTimeoutError` / Mongo errors** — MongoDB is not running or `MONGO_URI` is wrong. Confirm with `mongosh` or your Docker container.
- **Streamlit shows “Unavailable” for the API** — Start Uvicorn first; check `INTELLECTUAL_API_URL` and firewall/port usage.
- **401 / errors from Groq** — Invalid or missing `GROQ_API_KEY`; confirm the key in the Groq console.
- **Empty or failing chat list** — Same as Mongo: the UI loads `/api/v1/chats`, which reads the database.
