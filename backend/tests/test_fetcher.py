from app.services.fetcher import (
    build_blocked_content_message,
    detect_source_type,
    is_youtube_url,
    looks_like_blocked_content,
    normalize_text,
    normalize_url,
)


def test_detect_source_type_variants() -> None:
    assert detect_source_type("https://x.com/user/status/1") == "tweet"
    assert detect_source_type("https://reddit.com/r/python") == "reddit"
    assert detect_source_type("https://example.com/file.pdf") == "pdf"
    assert detect_source_type("https://example.com/post") == "article"


def test_detects_youtube_as_unsupported() -> None:
    assert is_youtube_url("https://youtu.be/abc123") is True
    assert is_youtube_url("https://www.youtube.com/watch?v=abc123") is True


def test_normalize_url_removes_tracking_and_fragment() -> None:
    normalized = normalize_url("https://example.com/post?utm_source=test&id=5#section")
    assert normalized == "https://example.com/post?id=5"


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("a   b\r\n\r\n\r\nc") == "a b\n\nc"


def test_detects_blocked_content_from_rate_limit_page() -> None:
    blocked = """
    Warning: Target URL returned error 429: Too Many Requests
    Our systems have detected unusual traffic from your computer network.
    This page checks to see if it's really you sending the requests, and not a robot.
    """
    assert looks_like_blocked_content(blocked) is True


def test_does_not_flag_normal_article_text_as_blocked() -> None:
    article = """
    Retrieval quality improves when chunks preserve context around the key technical decision.
    Memory systems should keep summaries concise and readable for later recall.
    """
    assert looks_like_blocked_content(article) is False


def test_blocked_message_is_generic() -> None:
    assert "blocked automated access" in build_blocked_content_message("article")
