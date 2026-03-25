from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class CaptureUrlRequest(BaseModel):
    url: HttpUrl


class CaptureTextRequest(BaseModel):
    text: str = Field(min_length=20)
    title: str | None = Field(default=None, max_length=200)


class CaptureStreamEvent(BaseModel):
    type: Literal["progress", "completed", "error"]
    stage: str
    message: str
    memory_id: UUID | None = None
    xp_awarded: int | None = None
    topics_updated: list[str] | None = None
    connections_found: int | None = None
    metadata: dict[str, Any] | None = None


class EnrichmentPayload(BaseModel):
    title: str | None = None
    summary: str
    key_concepts: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)
    content_type: str | None = None
    importance_score: float | None = None
    estimated_read_time: int | None = None


class CapturedContent(BaseModel):
    source_type: Literal["article", "pdf", "tweet", "reddit", "text"]
    source_url: str | None = None
    source_title: str | None = None
    raw_content: str


class PersistedCapture(BaseModel):
    memory_id: UUID
    xp_awarded: int
    topics_updated: list[str] = Field(default_factory=list)
    connections_found: int = 0
