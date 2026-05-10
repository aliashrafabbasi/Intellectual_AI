# Intellectual AI Chat

A **local full-stack chatbot**: a **FastAPI** backend streams answers from **Groq** (Llama-class models), **MongoDB** stores conversations, and a **React + TypeScript** web UI provides a ChatGPT-style interface with session history, search, and rename/delete controls.

The assistant persona is **“Jeffry the Genius”**—an intellectual, reasoning-focused helper (see `app/llm/prompts.py`). It defaults to **Roman Urdu** when you write in Urdu or Roman Urdu, and otherwise follows the user’s language.

---

## Quick start (any computer)

1. **Install [Python 3.11+](https://www.python.org/downloads/)**, **[Node.js 20+](https://nodejs.org/)**, and **[MongoDB](https://www.mongodb.com/try/download/community)** (or use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) in the cloud).
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

4. **Install Python dependencies:**

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Install frontend dependencies:**

   ```bash
   cd frontend && npm install && cd ..
   ```

6. **Configure environment** — copy `.env.example` to `.env` and set at least `GROQ_API_KEY` and `MONGO_URI` (see [Configuration](#configuration)).

   ```bash
   cp .env.example .env
   ```

7. **Initialize the database (once per machine / database):**

   ```bash
   python migratedb.py
   ```

   This checks MongoDB connectivity and creates indexes. MongoDB must already be running (or use a cloud URI).

8. **Run two terminals** (venv activated for the API terminal):

   **Terminal A — API**

   ```bash
   uvicorn main:app --reload
   ```

   **Terminal B — Web UI**

   ```bash
   cd frontend && npm run dev
   ```

9. Open the URL Vite prints (usually **http://localhost:5173**). By default the UI proxies `/api` to **http://127.0.0.1:8000**. You can also set `VITE_API_URL` in `frontend/.env` (see `frontend/.env.example`) or enter the API base URL under **Connection** in the sidebar.

To use the app from **another device on your LAN**, start Uvicorn with a public bind address, add that origin (including port) to `CORS_ORIGINS` in `.env`, and point the browser at your machine’s IP or set `VITE_API_URL` accordingly.

---

## What’s in the box

| Layer | Role |
|--------|------|
| **FastAPI** (`main.py`) | REST API under `/api/v1`: streaming chat, list/rename/delete sessions. |
| **Groq** (`groq` SDK) | LLM inference; model configurable via `.env`. |
| **MongoDB** (`pymongo`) | Persistent chats: `session_id`, messages, titles, timestamps. |
| **React + Vite** (`frontend/`) | Browser UI: streaming replies, sidebar conversations, responsive layout. |

You normally run **two processes**: the API (Uvicorn) and the frontend dev server (`npm run dev`). For production, run `npm run build` in `frontend/` and serve `frontend/dist/` behind nginx or similar with `/api` proxied to Uvicorn.

---

## Tech stack

- **Language:** Python 3.11+ (3.12 tested), TypeScript
- **Web API:** [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
- **Validation:** [Pydantic](https://docs.pydantic.dev/) v2
- **LLM:** [Groq](https://groq.com/) API via [`groq`](https://pypi.org/project/groq/)
- **Database:** [MongoDB](https://www.mongodb.com/) via [PyMongo](https://www.mongodb.com/docs/drivers/python/)
- **Frontend:** [React 18](https://react.dev/), [Vite](https://vitejs.dev/), [react-markdown](https://github.com/remarkjs/react-markdown)
- **Config:** [python-dotenv](https://pypi.org/project/python-dotenv/) (`.env` loaded in `main.py`, `app/core/config.py`)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| **Python 3.11+** | Use a venv so dependencies stay isolated per project. |
| **Node.js 20+** | For installing and building the frontend. |
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
   | `CORS_ORIGINS` | No | Comma-separated browser origins allowed to call the API (defaults include `http://localhost:5173`). |

   Legacy alias: `MONGO_URL` is still read if `MONGO_URI` is unset.

3. Optional **frontend** env (`frontend/.env`): `VITE_API_URL` — full base URL of the API when not using the Vite dev proxy (see `frontend/.env.example`).

---

## Running the app

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `python migratedb.py` | One-time DB check + indexes (after `.env` is set). |
| 2 | `uvicorn main:app --reload` | Starts the API at `http://127.0.0.1:8000`. |
| 3 | `cd frontend && npm run dev` | Starts the web UI (default **http://localhost:5173**). |

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

The React client uses the streaming endpoint for lower perceived latency.

---

## Project layout

```
Intellectual_AI/
├── main.py                 # FastAPI entry, CORS, loads .env
├── migratedb.py            # One-time MongoDB ping + indexes
├── requirements.txt        # Python dependencies (venv)
├── .env.example            # Template for secrets (copy to .env)
├── frontend/               # React + TypeScript (Vite)
│   ├── package.json
│   ├── vite.config.ts      # Dev proxy /api → backend
│   └── src/
├── app/
│   ├── api/v1/chat.py      # Chat routes
│   ├── core/config.py      # Settings from environment
│   ├── db/mongo.py         # Mongo client
│   ├── db/repositories.py  # Chat CRUD
│   ├── llm/groq_client.py  # Groq chat + stream
│   ├── llm/prompts.py      # System prompt / persona
│   └── services/chat_services.py
└── assets/                 # Optional static assets
```

---

## Troubleshooting

- **`ServerSelectionTimeoutError` / “Database unavailable”** — MongoDB is not running or `MONGO_URI` is wrong. Run `python migratedb.py` to verify. For local Mongo: `mongosh mongodb://127.0.0.1:27017`. For Atlas, use the SRV URI in `.env`.
- **`migratedb.py` fails** — Fix MongoDB reachability before starting Uvicorn.
- **Port 27017 already in use** — Another process uses that port; stop it or change Mongo’s port and update `MONGO_URI`.
- **Browser cannot reach API** — Start Uvicorn first; align `CORS_ORIGINS` with your UI origin; set `VITE_API_URL` if you are not using the Vite proxy.
- **401 / errors from Groq** — Invalid or missing `GROQ_API_KEY`.
- **`ModuleNotFoundError: app`** — Run commands from the **project root** directory with the venv activated.
