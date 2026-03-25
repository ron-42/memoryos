from datetime import date

from app.services.gamification import StreakState, update_streak, xp_for_source


def test_xp_for_known_source() -> None:
    assert xp_for_source("pdf") == 50


def test_update_streak_same_day() -> None:
    today = date(2026, 3, 24)
    state = StreakState(current_streak=3, longest_streak=3, last_capture_date=today)
    assert update_streak(state, today) == state


def test_update_streak_next_day() -> None:
    state = StreakState(current_streak=3, longest_streak=3, last_capture_date=date(2026, 3, 23))
    updated = update_streak(state, date(2026, 3, 24))
    assert updated.current_streak == 4
    assert updated.longest_streak == 4


def test_update_streak_gap_resets() -> None:
    state = StreakState(current_streak=6, longest_streak=6, last_capture_date=date(2026, 3, 20))
    updated = update_streak(state, date(2026, 3, 24))
    assert updated.current_streak == 1
    assert updated.longest_streak == 6
