from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.chat_services import (
    chat_with_ai,
    list_chats,
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
    )


@router.get("/chats")
def get_all_chats():
    return list_chats()


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