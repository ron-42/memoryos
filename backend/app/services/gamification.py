from dataclasses import dataclass
from datetime import date


XP_BY_SOURCE_TYPE = {
    "article": 20,
    "tweet": 20,
    "pdf": 50,
    "research": 50,
    "text": 20,
    "reddit": 20,
}


@dataclass(slots=True)
class StreakState:
    current_streak: int
    longest_streak: int
    last_capture_date: date | None


def xp_for_source(source_type: str) -> int:
    return XP_BY_SOURCE_TYPE.get(source_type, 20)


def update_streak(state: StreakState, today: date) -> StreakState:
    if state.last_capture_date == today:
        return state

    if state.last_capture_date is None:
        new_current = 1
    else:
        delta_days = (today - state.last_capture_date).days
        if delta_days == 1:
            new_current = state.current_streak + 1
        else:
            new_current = 1

    return StreakState(
        current_streak=new_current,
        longest_streak=max(state.longest_streak, new_current),
        last_capture_date=today,
    )
