from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.security import UserContext
from app.models.graph import GraphResponse
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def get_graph(user: UserContext = Depends(get_current_user)) -> GraphResponse:
    service = GraphService()
    return await service.build_graph(user.user_id)
