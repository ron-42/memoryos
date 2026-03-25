from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import UserContext
from app.models.stats import StatsResponse
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(user: UserContext = Depends(get_current_user)) -> StatsResponse:
    service = DashboardService()
    return await service.get_stats(user.user_id)
