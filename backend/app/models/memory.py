from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MemorySummary(BaseModel):
    id: UUID
    title: str | None
    source_type: str
    source_url: str | None
    topic_tags: list[str]
    content_type: str | None
    importance_score: float | None
    created_at: datetime


class MemoryConnection(BaseModel):
    id: UUID
    memory_id: UUID
    title: str | None
    similarity_score: float
    connection_label: str | None


class MemoryChunk(BaseModel):
    id: UUID
    chunk_index: int
    chunk_text: str


class MemoryDetail(BaseModel):
    id: UUID
    title: str | None
    source_type: str
    source_url: str | None
    source_title: str | None
    summary: str | None
    raw_content: str
    key_concepts: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    content_type: str | None
    importance_score: float | None
    estimated_read_time: int | None
    xp_awarded: int
    created_at: datetime
    connections: list[MemoryConnection] = Field(default_factory=list)
    chunks: list[MemoryChunk] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    items: list[MemorySummary]
    next_cursor: str | None = None
    limit: int
