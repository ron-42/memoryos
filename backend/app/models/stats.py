from pydantic import BaseModel, Field

from app.models.memory import MemorySummary
from app.models.topic import TopicProgress


class RecentConnection(BaseModel):
    id: str
    similarity_score: float
    connection_label: str | None = None
    discovered_at: str
    memory_a_id: str
    memory_a_title: str | None = None
    memory_b_id: str
    memory_b_title: str | None = None


class StatsResponse(BaseModel):
    current_streak: int
    longest_streak: int
    total_xp: int
    xp_today: int
    top_topics: list[TopicProgress] = Field(default_factory=list)
    recent_captures: list[MemorySummary] = Field(default_factory=list)
    recent_connections: list[RecentConnection] = Field(default_factory=list)

