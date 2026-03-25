from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException, status

from app.api.deps import get_current_user
from app.core.security import UserContext
from app.models.memory import MemoryListResponse
from app.services.repository import MemoryRepository

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("")
async def list_memories(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    topic: str | None = Query(default=None),
    content_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    user: UserContext = Depends(get_current_user),
) -> MemoryListResponse:
    repository = MemoryRepository()
    items, next_cursor = await repository.list_memories(
        user_id=user.user_id,
        limit=limit,
        cursor=cursor,
        topic=topic,
        content_type=content_type,
        query=q,
    )
    return MemoryListResponse(items=items, next_cursor=next_cursor, limit=limit)


@router.get("/{memory_id}")
async def get_memory(memory_id: str, user: UserContext = Depends(get_current_user)):
    repository = MemoryRepository()
    try:
        memory_uuid = UUID(memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid memory id") from exc

    detail = await repository.get_memory_detail(memory_id=memory_uuid, user_id=user.user_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return detail
