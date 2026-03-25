from datetime import datetime, timezone
from uuid import UUID

from app.models.stats import RecentConnection, StatsResponse
from app.models.topic import TopicsResponse
from app.services.repository import MemoryRepository


class DashboardService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    async def get_topics(self, user_id: UUID) -> TopicsResponse:
        items = await self.repository.get_topics_progress(user_id=user_id, limit=20)
        return TopicsResponse(items=items)

    async def get_stats(self, user_id: UUID) -> StatsResponse:
        profile = await self.repository.get_profile_stats(user_id=user_id)
        topics = await self.repository.get_topics_progress(user_id=user_id, limit=4)
        recent_captures, _ = await self.repository.list_memories(user_id=user_id, limit=5)
        recent_connections_rows = await self.repository.get_recent_connections(user_id=user_id, limit=5)

        memory_ids = {UUID(row["memory_a"]) for row in recent_connections_rows} | {UUID(row["memory_b"]) for row in recent_connections_rows}
        memory_map = await self.repository.get_memories_by_ids(user_id=user_id, memory_ids=list(memory_ids)) if memory_ids else {}

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        xp_events = await self.repository.get_xp_events_since(user_id=user_id, iso_timestamp=today_start)
        xp_today = sum(int(row.get("xp_amount") or 0) for row in xp_events)

        recent_connections = [
            RecentConnection(
                id=row["id"],
                similarity_score=float(row["similarity_score"]),
                connection_label=row.get("connection_label"),
                discovered_at=row["discovered_at"],
                memory_a_id=row["memory_a"],
                memory_a_title=memory_map.get(row["memory_a"], {}).get("title"),
                memory_b_id=row["memory_b"],
                memory_b_title=memory_map.get(row["memory_b"], {}).get("title"),
            )
            for row in recent_connections_rows
        ]

        return StatsResponse(
            current_streak=int(profile.get("current_streak") or 0),
            longest_streak=int(profile.get("longest_streak") or 0),
            total_xp=int(profile.get("total_xp") or 0),
            xp_today=xp_today,
            top_topics=topics,
            recent_captures=recent_captures,
            recent_connections=recent_connections,
        )
