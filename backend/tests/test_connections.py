from uuid import uuid4

from app.services.connections import build_connection_label, cosine_similarity
from app.services.repository import canonical_memory_pair


def test_canonical_memory_pair_sorts_ids() -> None:
    left = uuid4()
    right = uuid4()
    first, second = canonical_memory_pair(left, right)
    assert str(first) < str(second)


def test_cosine_similarity_matches_identical_vectors() -> None:
    assert round(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 5) == 1.0


def test_connection_label_prefers_topic_overlap() -> None:
    label = build_connection_label(
        current={"topic_tags": ["AI/ML", "Engineering"], "source_type": "article"},
        candidate={"topic_tags": ["AI/ML"], "source_type": "article"},
    )
    assert "AI/ML" in label
