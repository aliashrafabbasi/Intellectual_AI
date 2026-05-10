from datetime import datetime

from app.db.mongo import chats_collection


def get_chat(session_id: str):
    return chats_collection.find_one({"session_id": session_id})


def get_chat_messages_tail(session_id: str, limit: int) -> list | None:
    """
    Return only the last `limit` messages (smaller payload than full find_one for long chats).
    None if the session document does not exist.
    """
    doc = chats_collection.find_one(
        {"session_id": session_id},
        {"messages": {"$slice": -limit}},
    )
    if doc is None:
        return None
    return doc.get("messages") or []

def create_chat(session_id: str):
    chat = {
        "session_id": session_id,
        "name": "Untitled chat",
        "messages": [],
        "created_at": datetime.utcnow(),
    }
    chats_collection.insert_one(chat)
    return chat


def ensure_chat(session_id: str) -> dict:
    """Return existing chat or insert an empty one (for sidebar list before first message)."""
    existing = get_chat(session_id)
    if existing:
        existing.pop("_id", None)
        return existing
    chat = create_chat(session_id)
    if isinstance(chat, dict) and "_id" in chat:
        chat.pop("_id", None)
    return chat

def add_messages(session_id:str , role:str,content:str):
    chats_collection.update_one(
        {"session_id":session_id},
        {"$push":{"message":{"role":role ,"content":content}}}
    )


def get_all_chats():
    """Full documents (includes messages). Prefer list_chat_summaries for listing."""
    return list(chats_collection.find({}, {"_id": 0}))


def list_chat_summaries():
    """Sidebar list only — excludes messages so large histories cannot stall /api/v1/chats."""
    cur = chats_collection.find({}, {"_id": 0, "messages": 0}).sort("created_at", -1)
    return list(cur)


def get_chat_document(session_id: str) -> dict | None:
    doc = chats_collection.find_one({"session_id": session_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc

def delete_chat_by_session(session_id: str):
    result = chats_collection.delete_one({"session_id": session_id})
    return {"deleted_count": result.deleted_count}


def update_session_name(session_id: str, name: str) -> dict:
    result = chats_collection.update_one(
        {"session_id": session_id},
        {"$set": {"name": name.strip()}},
    )
    return {"matched_count": result.matched_count, "modified_count": result.modified_count}


def add_message(session_id: str, role: str, content: str):
    chats_collection.update_one(
        {"session_id": session_id},
        {
            "$push": {
                "messages": {
                    "role": role,
                    "content": content
                }
            }
        }
    )


def add_message_pair(session_id: str, user_content: str, assistant_content: str) -> None:
    chats_collection.update_one(
        {"session_id": session_id},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": assistant_content},
                    ]
                }
            }
        },
    )
