import logging

from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.services.maintenance import MaintenanceService

logger = logging.getLogger(__name__)


async def run_connection_backfill_job() -> None:
    service = MaintenanceService()
    result = await service.backfill_connections()
    logger.info("connection backfill job finished", extra=result)


async def run_topic_maintenance_job() -> None:
    service = MaintenanceService()
    result = await service.refresh_topics()
    logger.info("topic maintenance job finished", extra=result)


def build_scheduler() -> AsyncIOScheduler | None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        return None

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_connection_backfill_job,
        CronTrigger(hour=settings.connection_backfill_hour_utc),
        id="connection_backfill",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        run_topic_maintenance_job,
        CronTrigger(hour=settings.topic_maintenance_hour_utc),
        id="topic_maintenance",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    return scheduler
