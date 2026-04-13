from datetime import datetime

from app.db.mongo import chats_collection


def get_chat(session_id: str):
    return chats_collection.find_one({"session_id":session_id})

def create_chat(session_id: str):
    chat = {
        "session_id": session_id,
        "name": "Untitled chat",
        "messages": [],
        "created_at": datetime.utcnow(),
    }
    chats_collection.insert_one(chat)
    return chat

def add_messages(session_id:str , role:str,content:str):
    chats_collection.update_one(
        {"session_id":session_id},
        {"$push":{"message":{"role":role ,"content":content}}}
    )


def get_all_chats():
    return list(chats_collection.find({},{"_id":0}))

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
