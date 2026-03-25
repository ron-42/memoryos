import logging
from dataclasses import dataclass
from uuid import UUID

from app.db.pinecone import get_pinecone_client
from app.services.embedder import EmbedderService
from app.services.repository import MemoryRepository

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class RetrievalItem:
    memory_id: UUID
    title: str | None
    source_url: str | None
    chunk_text: str
    similarity: float


class RetrieverService:
    def __init__(
        self,
        repository: MemoryRepository | None = None,
        embedder: EmbedderService | None = None,
    ) -> None:
        self.repository = repository or MemoryRepository()
        self.embedder = embedder or EmbedderService()

    async def retrieve(self, query: str, user_id: UUID, top_k: int = 5) -> list[RetrievalItem]:
        dense_results = await self._dense_search(query=query, user_id=user_id)
        keyword_results = await self.repository.get_chunk_keyword_matches(user_id=user_id, query=query, limit=12)
        merged = self._reciprocal_rank_fusion(dense_results=dense_results, keyword_results=keyword_results, top_k=top_k)
        memory_map = await self.repository.get_memories_by_ids(
            user_id=user_id,
            memory_ids=[item.memory_id for item in merged],
        )

        return [
            RetrievalItem(
                memory_id=item.memory_id,
                title=memory_map.get(str(item.memory_id), {}).get("title"),
                source_url=memory_map.get(str(item.memory_id), {}).get("source_url"),
                chunk_text=item.chunk_text,
                similarity=item.similarity,
            )
            for item in merged
        ]

    async def _dense_search(self, query: str, user_id: UUID) -> list[dict[str, object]]:
        embedding = await self.embedder.embed_query(query)
        pinecone = await get_pinecone_client()
        if pinecone is None:
            return []
        try:
            try:
                matches = await pinecone.query(
                    vector=embedding,
                    top_k=12,
                    filter={
                        "record_type": {"$eq": "chunk"},
                        "user_id": {"$eq": str(user_id)},
                    },
                    include_metadata=True,
                    include_values=False,
                )
                results: list[dict[str, object]] = []
                for match in matches:
                    metadata = match.get("metadata") or {}
                    memory_id = metadata.get("memory_id")
                    chunk_id = metadata.get("chunk_id")
                    chunk_text = metadata.get("chunk_text")
                    if not memory_id or not chunk_id or not chunk_text:
                        continue
                    results.append(
                        {
                            "id": chunk_id,
                            "memory_id": memory_id,
                            "chunk_text": chunk_text,
                            "similarity": float(match.get("score") or 0.0),
                        }
                    )
                return results
            except Exception:
                logger.exception("pinecone dense search failed user_id=%s", user_id)
                return []
        finally:
            await pinecone.aclose()

    def _reciprocal_rank_fusion(
        self,
        dense_results: list[dict[str, object]],
        keyword_results: list[dict[str, object]],
        top_k: int,
    ) -> list[RetrievalItem]:
        scores: dict[tuple[str, str], float] = {}
        payloads: dict[tuple[str, str], tuple[UUID, str, float]] = {}

        for rank, item in enumerate(dense_results, start=1):
            key = (str(item["memory_id"]), str(item["id"]))
            scores[key] = scores.get(key, 0.0) + (1 / (60 + rank))
            payloads[key] = (
                UUID(str(item["memory_id"])),
                str(item["chunk_text"]),
                float(item.get("similarity") or 0.0),
            )

        for rank, item in enumerate(keyword_results, start=1):
            key = (str(item["memory_id"]), str(item["id"]))
            scores[key] = scores.get(key, 0.0) + (1 / (60 + rank))
            existing_similarity = payloads.get(key, (UUID(str(item["memory_id"])), str(item["chunk_text"]), 0.0))[2]
            payloads[key] = (
                UUID(str(item["memory_id"])),
                str(item["chunk_text"]),
                max(existing_similarity, 0.3),
            )

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [
            RetrievalItem(
                memory_id=payloads[key][0],
                title=None,
                source_url=None,
                chunk_text=payloads[key][1],
                similarity=payloads[key][2],
            )
            for key, _ in ranked
        ]
