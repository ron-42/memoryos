import logging
from uuid import UUID

from app.core.config import get_settings
from app.models.topic import TopicAggregate
from app.services.connections import ConnectionService
from app.services.repository import MemoryRepository
from app.services.topics import color_for_topic, level_for_xp

logger = logging.getLogger(__name__)


def aggregate_topics_from_memories(memories: list[dict[str, object]]) -> list[TopicAggregate]:
    aggregates: dict[str, tuple[int, int]] = {}
    for memory in memories:
        topic_tags = list(memory.get("topic_tags") or [])
        xp_awarded = int(memory.get("xp_awarded") or 0)
        if not topic_tags:
            continue
        xp_per_topic = max(1, xp_awarded // len(topic_tags))
        for topic_name in topic_tags:
            current_count, current_xp = aggregates.get(topic_name, (0, 0))
            aggregates[topic_name] = (current_count + 1, current_xp + xp_per_topic)

    return [
        TopicAggregate(
            name=name,
            memory_count=memory_count,
            total_xp=total_xp,
            level=level_for_xp(total_xp),
            color=color_for_topic(name),
        )
        for name, (memory_count, total_xp) in sorted(aggregates.items(), key=lambda item: item[1][1], reverse=True)
    ]


class MaintenanceService:
    def __init__(
        self,
        repository: MemoryRepository | None = None,
        connections: ConnectionService | None = None,
    ) -> None:
        self.repository = repository or MemoryRepository()
        self.connections = connections or ConnectionService(repository=self.repository)
        self.settings = get_settings()

    async def backfill_connections(self) -> dict[str, int]:
        user_ids = await self.repository.list_user_ids(limit=self.settings.job_user_batch_limit)
        users_processed = 0
        discoveries = 0

        for user_id in user_ids:
            memory_ids = await self.repository.list_memory_ids_without_connections(
                user_id=user_id,
                limit=self.settings.job_memory_batch_limit,
            )
            if not memory_ids:
                continue
            users_processed += 1
            for memory_id in memory_ids:
                discovered = await self.connections.discover_for_memory(memory_id=memory_id, user_id=user_id)
                discoveries += len(discovered)

        logger.info("connection backfill completed", extra={"users_processed": users_processed, "discoveries": discoveries})
        return {"users_processed": users_processed, "discoveries": discoveries}

    async def refresh_topics(self) -> dict[str, int]:
        user_ids = await self.repository.list_user_ids(limit=self.settings.job_user_batch_limit)
        users_processed = 0

        for user_id in user_ids:
            memories = await self.repository.list_memories_for_topic_rebuild(user_id=user_id, limit=1000)
            aggregates = aggregate_topics_from_memories(memories)
            await self.repository.sync_topics_for_user(user_id=user_id, aggregates=aggregates)
            users_processed += 1

        logger.info("topic maintenance completed", extra={"users_processed": users_processed})
        return {"users_processed": users_processed}
