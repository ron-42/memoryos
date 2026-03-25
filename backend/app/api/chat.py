from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.security import UserContext
from app.models.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("")
async def chat(payload: ChatRequest, user: UserContext = Depends(get_current_user)) -> StreamingResponse:
    service = ChatService()
    return StreamingResponse(
        service.stream_chat(payload.query, user.user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
