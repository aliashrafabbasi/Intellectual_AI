from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.chat_services import (
    chat_with_ai,
    ensure_session_document,
    list_chats,
    load_chat,
    remove_chat,
    rename_session,
    stream_chat_with_ai,
)

router = APIRouter()


class ChatBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class RenameBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


@router.post("/chat")
def chat(session_id: str, message: str):
    reply = chat_with_ai(session_id, message)
    return {"session_id": session_id, "reply": reply}


@router.post("/chat/stream")
def chat_stream(body: ChatBody):
    return StreamingResponse(
        stream_chat_with_ai(body.session_id, body.message),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            # Behind nginx: disable buffering so tokens flush immediately
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chats")
def get_all_chats():
    return list_chats()


@router.post("/chat/{session_id}/ensure")
def ensure_chat_session(session_id: str):
    """Create an empty chat row if missing so the client can show it in the list immediately."""
    return ensure_session_document(session_id)


@router.get("/chat/{session_id}")
def get_chat(session_id: str):
    doc = load_chat(session_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return doc


@router.patch("/chat/{session_id}")
def rename_chat(session_id: str, body: RenameBody):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty.")
    result = rename_session(session_id, name)
    if result.get("matched_count", 0) == 0:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return {"session_id": session_id, "name": name}


@router.delete("/chat/{session_id}")
def delete_chat(session_id: str):
    result = remove_chat(session_id)
    if result.get("deleted_count", 0) == 0:
        raise HTTPException(status_code=404, detail="Chat Not Found!")
    return {"message": "Chat deleted successfully."}