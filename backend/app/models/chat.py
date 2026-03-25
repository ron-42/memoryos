from pydantic import BaseModel, Field


class ChatCitation(BaseModel):
    memory_id: str
    title: str | None
    source_url: str | None
    similarity: float
    excerpt: str


class ChatCompletedEvent(BaseModel):
    type: str = "completed"
    answer: str
    citations: list[ChatCitation]


class ChatRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
