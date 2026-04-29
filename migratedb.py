#!/usr/bin/env python3
"""
One-time MongoDB initialization for Intellectual AI.

Run once per machine (after MongoDB is running and `.env` has `MONGO_URI`):

    python migratedb.py

This pings the server, ensures the `chats` collection is reachable, and creates
indexes used by the API. Safe to run multiple times (indexes are idempotent).
"""

from __future__ import annotations

import sys


def main() -> int:
    # Load .env before any app imports that read MONGO_URI
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from app.db.mongo import chats_collection, client, db
    except Exception as e:
        print(
            f"Failed to load database config: {e}\n"
            "Activate your venv and run this script from the project root.",
            file=sys.stderr,
        )
        return 1

    try:
        client.admin.command("ping")
    except Exception as e:
        print(
            "Cannot connect to MongoDB. Start MongoDB (or fix MONGO_URI in `.env`).\n"
            f"Details: {e}",
            file=sys.stderr,
        )
        return 1

    print(f"OK — MongoDB reachable (database `{db.name}`, collection `{chats_collection.name}`).")

    try:
        chats_collection.create_index("session_id", unique=True, name="idx_session_id_unique")
        print("Index ready: session_id (unique).")
    except Exception as e:
        print(
            f"Warning: unique index on session_id was not created "
            f"(you may have duplicate session_id values): {e}",
            file=sys.stderr,
        )

    try:
        chats_collection.create_index([("created_at", -1)], name="idx_created_at_desc")
        print("Index ready: created_at (descending).")
    except Exception as e:
        print(f"Warning: created_at index was not created: {e}", file=sys.stderr)

    print("\nNext steps:\n  • API:  uvicorn main:app --reload\n  • UI:   streamlit run streamlit_app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
