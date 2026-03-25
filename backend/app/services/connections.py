import logging
import math
from uuid import UUID

from app.db.pinecone import get_pinecone_client
from app.services.repository import MemoryRepository

logger = logging.getLogger(__name__)

class ConnectionService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or MemoryRepository()

    async def discover_for_memory(self, memory_id: UUID, user_id: UUID) -> list[dict[str, object]]:
        current = await self.repository.get_memory_similarity_payload(user_id=user_id, memory_id=memory_id)
        if not current or not current.get("embedding"):
            return []

        pinecone_matches = await self._query_pinecone_memory_matches(memory_id=memory_id, current=current)
        if pinecone_matches:
            connected_ids = await self.repository.get_connected_memory_ids(user_id=user_id, memory_id=memory_id)
            discovered: list[dict[str, object]] = []
            for similarity, candidate in pinecone_matches:
                candidate_id = str(candidate["id"])
                if candidate_id in connected_ids:
                    continue
                if current.get("source_url") and candidate.get("source_url") and current.get("source_url") == candidate.get("source_url"):
                    continue
                label = build_connection_label(current=current, candidate=candidate)
                inserted = await self.repository.create_connection(
                    user_id=user_id,
                    memory_a=memory_id,
                    memory_b=UUID(candidate_id),
                    similarity_score=round(similarity, 4),
                    connection_label=label,
                )
                if inserted:
                    discovered.append(inserted)
                if len(discovered) >= 3:
                    break
            return discovered

        candidates = await self.repository.get_connection_candidates(user_id=user_id, exclude_memory_id=memory_id, limit=50)
        connected_ids = await self.repository.get_connected_memory_ids(user_id=user_id, memory_id=memory_id)

        scored_candidates: list[tuple[float, dict[str, object]]] = []
        current_embedding = parse_embedding(current.get("embedding"))
        for candidate in candidates:
            candidate_id = str(candidate["id"])
            if candidate_id in connected_ids:
                continue
            if current.get("source_url") and candidate.get("source_url") and current.get("source_url") == candidate.get("source_url"):
                continue
            candidate_embedding = parse_embedding(candidate.get("embedding"))
            if not candidate_embedding:
                continue
            similarity = cosine_similarity(current_embedding, candidate_embedding)
            if similarity >= 0.75:
                scored_candidates.append((similarity, candidate))

        discovered: list[dict[str, object]] = []
        for similarity, candidate in sorted(scored_candidates, key=lambda item: item[0], reverse=True)[:3]:
            label = build_connection_label(current=current, candidate=candidate)
            inserted = await self.repository.create_connection(
                user_id=user_id,
                memory_a=memory_id,
                memory_b=UUID(str(candidate["id"])),
                similarity_score=round(similarity, 4),
                connection_label=label,
            )
            if inserted:
                discovered.append(inserted)
        return discovered

    async def _query_pinecone_memory_matches(
        self,
        memory_id: UUID,
        current: dict[str, object],
    ) -> list[tuple[float, dict[str, object]]]:
        pinecone = await get_pinecone_client()
        if pinecone is None:
            return []
        try:
            current_embedding = parse_embedding(current.get("embedding"))
            if not current_embedding:
                return []
            matches = await pinecone.query(
                vector=current_embedding,
                top_k=8,
                filter={
                    "record_type": {"$eq": "memory"},
                    "user_id": {"$eq": str(current.get("user_id"))},
                },
                include_metadata=True,
                include_values=False,
            )
            scored: list[tuple[float, dict[str, object]]] = []
            for match in matches:
                metadata = match.get("metadata") or {}
                candidate_id = metadata.get("memory_id")
                if not candidate_id or candidate_id == str(memory_id):
                    continue
                similarity = float(match.get("score") or 0.0)
                if similarity < 0.75:
                    continue
                scored.append(
                    (
                        similarity,
                        {
                            "id": candidate_id,
                            "topic_tags": metadata.get("topic_tags") or [],
                            "source_type": metadata.get("source_type"),
                            "source_url": metadata.get("source_url"),
                        },
                    )
                )
            return scored
        except Exception:
            logger.exception("pinecone memory connection query failed memory_id=%s", memory_id)
            return []
        finally:
            await pinecone.aclose()


def parse_embedding(value: object) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip("[] ")
        if not stripped:
            return []
        return [float(part) for part in stripped.split(",")]
    return []


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def build_connection_label(current: dict[str, object], candidate: dict[str, object]) -> str:
    current_topics = set(current.get("topic_tags") or [])
    candidate_topics = set(candidate.get("topic_tags") or [])
    overlap = sorted(current_topics & candidate_topics)
    if overlap:
        return f"Both connect through {', '.join(overlap[:2])}."
    if current.get("source_type") == candidate.get("source_type"):
        return f"Both captures come from the same source type: {current.get('source_type')}."
    return "These memories are semantically related based on their content."
