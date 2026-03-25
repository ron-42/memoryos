from collections import defaultdict
from uuid import UUID

from app.models.graph import GraphEdge, GraphNode, GraphResponse
from app.services.repository import MemoryRepository
from app.services.topics import color_for_topic


class GraphService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    async def build_graph(self, user_id: UUID) -> GraphResponse:
        topics = await self.repository.get_topics_progress(user_id=user_id, limit=50)
        connections = await self.repository.get_all_connections(user_id=user_id, limit=200)
        memory_ids = {UUID(row["memory_a"]) for row in connections} | {UUID(row["memory_b"]) for row in connections}
        memories = await self.repository.get_memories_by_ids(user_id=user_id, memory_ids=list(memory_ids)) if memory_ids else {}

        edge_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
        for connection in connections:
            left_topics = memories.get(connection["memory_a"], {}).get("topic_tags") or []
            right_topics = memories.get(connection["memory_b"], {}).get("topic_tags") or []
            for left_topic in left_topics:
                for right_topic in right_topics:
                    if left_topic == right_topic:
                        continue
                    key = tuple(sorted((left_topic, right_topic)))
                    edge_scores[key].append(float(connection["similarity_score"]))

        nodes = [
            GraphNode(
                id=topic.name,
                label=topic.name,
                level=topic.level,
                memory_count=topic.memory_count,
                color=topic.color or color_for_topic(topic.name),
            )
            for topic in topics
        ]
        edges = [
            GraphEdge(source=source, target=target, strength=round(sum(scores) / len(scores), 4))
            for (source, target), scores in edge_scores.items()
        ]
        return GraphResponse(nodes=nodes, edges=edges)

