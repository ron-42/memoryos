TOPIC_LEVEL_THRESHOLDS = [0, 50, 150, 300, 500, 800, 1200, 1800, 2600, 3500]


def level_for_xp(xp: int) -> int:
    level = 1
    for index, threshold in enumerate(TOPIC_LEVEL_THRESHOLDS, start=1):
        if xp >= threshold:
            level = index
    return level


def color_for_topic(name: str) -> str:
    palette = [
        "#4F46E5",
        "#0F766E",
        "#D97706",
        "#DC2626",
        "#7C3AED",
        "#0891B2",
        "#65A30D",
        "#BE185D",
    ]
    return palette[sum(ord(char) for char in name) % len(palette)]
