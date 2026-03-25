from app.services.topics import color_for_topic, level_for_xp


def test_level_for_xp_thresholds() -> None:
    assert level_for_xp(0) == 1
    assert level_for_xp(50) == 2
    assert level_for_xp(3500) == 10


def test_color_for_topic_is_deterministic() -> None:
    assert color_for_topic("AI/ML") == color_for_topic("AI/ML")
