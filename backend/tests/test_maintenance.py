from app.services.maintenance import aggregate_topics_from_memories


def test_aggregate_topics_from_memories_rolls_up_counts_and_xp() -> None:
    aggregates = aggregate_topics_from_memories(
        [
            {"topic_tags": ["AI/ML", "Engineering"], "xp_awarded": 30},
            {"topic_tags": ["AI/ML"], "xp_awarded": 20},
            {"topic_tags": ["Research"], "xp_awarded": 50},
        ]
    )

    by_name = {item.name: item for item in aggregates}
    assert by_name["AI/ML"].memory_count == 2
    assert by_name["AI/ML"].total_xp == 35
    assert by_name["Engineering"].memory_count == 1
    assert by_name["Research"].total_xp == 50
