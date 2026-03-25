from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    level: int
    memory_count: int
    color: str


class GraphEdge(BaseModel):
    source: str
    target: str
    strength: float


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

