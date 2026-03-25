import logging

from app.core.config import get_settings
from app.core.security import UserContext

logger = logging.getLogger(__name__)

async def get_current_user() -> UserContext:
    settings = get_settings()
    logger.debug("auth disabled using local single-user context")
    return UserContext(user_id=settings.local_user_id, email=settings.local_user_email)
