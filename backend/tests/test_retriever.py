from uuid import uuid4

from app.services.retriever import RetrieverService


def test_rrf_prefers_items_seen_in_both_lists() -> None:
    service = RetrieverService()
    shared_memory_id = uuid4()
    merged = service._reciprocal_rank_fusion(
        dense_results=[
            {"id": str(uuid4()), "memory_id": str(shared_memory_id), "chunk_text": "dense shared", "similarity": 0.9},
        ],
        keyword_results=[
            {"id": str(uuid4()), "memory_id": str(shared_memory_id), "chunk_text": "keyword shared"},
        ],
        top_k=5,
    )
    assert merged
    assert merged[0].memory_id == shared_memory_id
