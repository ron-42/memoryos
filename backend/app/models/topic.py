from dataclasses import dataclass

from pydantic import BaseModel


class TopicProgress(BaseModel):
    id: str
    name: str
    memory_count: int
    total_xp: int
    level: int
    color: str | None = None


class TopicsResponse(BaseModel):
    items: list[TopicProgress]


@dataclass(slots=True)
class TopicAggregate:
    name: str
    memory_count: int
    total_xp: int
    level: int
    color: str
