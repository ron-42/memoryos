from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import UserContext
from app.models.topic import TopicsResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("")
async def get_topics(user: UserContext = Depends(get_current_user)) -> TopicsResponse:
    service = DashboardService()
    return await service.get_topics(user.user_id)
