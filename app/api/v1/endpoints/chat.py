from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api import deps
from app.db.models import User
from app.engine.chat import chat_engine

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str

@router.post("/", response_model=ChatResponse)
async def chat_with_akira(
    request: ChatRequest,
    current_user: User = Depends(deps.get_current_user)
):
    # Prepare messages for the chat engine
    formatted_messages = [
        {"role": "system", "content": "Bạn là Akira, một trợ lý học tiếng Nhật thông minh, thân thiện và hài hước. Bạn luôn sẵn sàng giúp đỡ người dùng học tiếng Nhật và văn hóa Nhật Bản."}
    ]
    for msg in request.messages:
        formatted_messages.append({"role": msg.role, "content": msg.content})
        
    response_text = chat_engine.generate_response(formatted_messages)
    return ChatResponse(response=response_text)
