# Intellectual AI Chat

A **local full-stack chatbot**: a **FastAPI** backend streams answers from **Groq** (Llama-class models), **MongoDB** stores conversations, and a **Streamlit** web app provides a ChatGPT-style interface with session history, search, and rename/delete controls.

The assistant persona is **“Jeffry the Genius”**—an intellectual, reasoning-focused helper (see `app/llm/prompts.py`). It defaults to **Roman Urdu** when you write in Urdu or Roman Urdu, and otherwise follows the user’s language.

---

## Quick start (any computer)

1. **Install [Python 3.11+](https://www.python.org/downloads/)** and **[MongoDB](https://www.mongodb.com/try/download/community)** (or use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) in the cloud).
2. **Clone or copy** this project folder to the machine.
3. Open a terminal **in the project root** and run:

   ```bash
   python -m venv venv
   ```

   **Activate the virtual environment:**

   | OS | Command |
   |----|---------|
   | Linux / macOS | `source venv/bin/activate` |
   | Windows (cmd) | `venv\Scripts\activate.bat` |
   | Windows (PowerShell) | `venv\Scripts\Activate.ps1` |

4. **Install dependencies:**

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Configure environment** — copy `.env.example` to `.env` and set at least `GROQ_API_KEY` and `MONGO_URI` (see [Configuration](#configuration)).

   ```bash
   cp .env.example .env
   ```

6. **Initialize the database (once per machine / database):**

   ```bash
   python migratedb.py
   ```

   This checks MongoDB connectivity and creates indexes. MongoDB must already be running (or use a cloud URI).

7. **Run two terminals** (both with the venv activated):

   **Terminal A — API**

   ```bash
   uvicorn main:app --reload
   ```

   **Terminal B — UI**

   ```bash
   streamlit run streamlit_app.py
   ```

8. Open the URL Streamlit prints (usually **http://localhost:8501**). The UI talks to the API at `INTELLECTUAL_API_URL` in `.env` (default **http://127.0.0.1:8000**).

To use the app from **another device on your LAN**, start Uvicorn with a public bind address and point `INTELLECTUAL_API_URL` at that host (firewall permitting):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## What’s in the box

| Layer | Role |
|--------|------|
| **FastAPI** (`main.py`) | REST API under `/api/v1`: streaming chat, list/rename/delete sessions. |
| **Groq** (`groq` SDK) | LLM inference; model configurable via `.env`. |
| **MongoDB** (`pymongo`) | Persistent chats: `session_id`, messages, titles, timestamps. |
| **Streamlit** (`streamlit_app.py`) | Browser UI: streaming replies, sidebar conversations, search, connection status. |

You normally run **two processes**: the API (Uvicorn) and the UI (Streamlit). The UI calls the API using `INTELLECTUAL_API_URL` from `.env`.

---

## Tech stack

- **Language:** Python 3.11+ (3.12 tested)
- **Web API:** [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- **Validation:** [Pydantic](https://docs.pydantic.dev/) v2
- **LLM:** [Groq](https://groq.com/) API via [`groq`](https://pypi.org/project/groq/)
- **Database:** [MongoDB](https://www.mongodb.com/) via [PyMongo](https://www.mongodb.com/docs/drivers/python/)
- **Frontend:** [Streamlit](https://streamlit.io/)
- **HTTP (UI → API):** [HTTPX](https://www.python-httpx.org/), [Requests](https://requests.readthedocs.io/)
- **Config:** [python-dotenv](https://pypi.org/project/python-dotenv/) (`.env` loaded in `main.py`, `app/core/config.py`, and `streamlit_app.py`)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.11+** | Use a venv so dependencies stay isolated per project. |
| **MongoDB** | Local install, Docker, or Atlas — must match `MONGO_URI` in `.env`. |
| **Groq API key** | Create one at the [Groq Console](https://console.groq.com/). |

---

## Database setup (`migratedb.py`)

Run **once** after MongoDB is available and `.env` is configured:

```bash
python migratedb.py
```

This script:

- **Pings** MongoDB (fails fast if the server or URI is wrong).
- **Creates indexes** on the `chats` collection (`session_id` unique, `created_at` for listing). Running it again is safe.

It does **not** seed demo data; collections are created automatically when you first save a chat.

---

## Configuration

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit **`.env`** (never commit it; it is listed in `.gitignore`):

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `GROQ_API_KEY` | **Yes** | Groq API key. |
   | `MONGO_URI` | **Yes** in practice | MongoDB connection string (default in `.env.example`: local `mongodb://127.0.0.1:27017`). |
   | `GROQ_MODEL` | No | Model id (default: `llama-3.1-8b-instant`). |
   | `GROQ_MAX_TOKENS` | No | Max tokens (default: `4096`). |
   | `INTELLECTUAL_API_URL` | No | Base URL of the FastAPI app for Streamlit (default: `http://127.0.0.1:8000`). |

   Legacy alias: `MONGO_URL` is still read if `MONGO_URI` is unset.

---

## Running the app

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `python migratedb.py` | One-time DB check + indexes (after `.env` is set). |
| 2 | `uvicorn main:app --reload` | Starts the API at `http://127.0.0.1:8000`. |
| 3 | `streamlit run streamlit_app.py` | Starts the web UI (default **http://localhost:8501**). |

- Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## API overview (prefix `/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat/stream` | Stream assistant reply (`session_id`, `message` in JSON body). |
| `POST` | `/chat` | Non-streaming chat (query params `session_id`, `message`). |
| `POST` | `/chat/{session_id}/ensure` | Ensure an empty session exists (UI “New chat”). |
| `GET` | `/chats` | List stored chats. |
| `GET` | `/chat/{session_id}` | Load one chat. |
| `PATCH` | `/chat/{session_id}` | Rename a session (`name` in JSON body). |
| `DELETE` | `/chat/{session_id}` | Delete a session. |

The Streamlit client uses the streaming endpoint for lower perceived latency.

---

## Project layout

```
Intellectual_AI/
├── main.py                 # FastAPI entry, loads .env
├── streamlit_app.py        # Streamlit UI
├── migratedb.py            # One-time MongoDB ping + indexes
├── requirements.txt        # Python dependencies (venv)
├── .env.example            # Template for secrets (copy to .env)
├── app/
│   ├── api/v1/chat.py      # Chat routes
│   ├── core/config.py      # Settings from environment
│   ├── db/mongo.py         # Mongo client
│   ├── db/repositories.py  # Chat CRUD
│   ├── llm/groq_client.py  # Groq chat + stream
│   ├── llm/prompts.py      # System prompt / persona
│   └── services/chat_services.py
├── assets/                 # Chat avatars (user / AI), optional
└── .streamlit/config.toml  # Streamlit theme defaults
```

---

## Troubleshooting

- **`ServerSelectionTimeoutError` / “Database unavailable”** — MongoDB is not running or `MONGO_URI` is wrong. Run `python migratedb.py` to verify. For local Mongo: `mongosh mongodb://127.0.0.1:27017`. For Atlas, use the SRV URI in `.env`.
- **`migratedb.py` fails** — Fix MongoDB reachability before starting Uvicorn or Streamlit.
- **Port 27017 already in use** — Another process uses that port; stop it or change Mongo’s port and update `MONGO_URI`.
- **Streamlit shows “Unavailable” for the API** — Start Uvicorn first; align `INTELLECTUAL_API_URL` with the host/port Uvicorn uses.
- **401 / errors from Groq** — Invalid or missing `GROQ_API_KEY`.
- **`ModuleNotFoundError: app`** — Run commands from the **project root** directory with the venv activated.
# Intellectual_AI
