from datetime import datetime, time

from config import WORK_HOURS_END, WORK_HOURS_START


def is_within_work_hours(now: datetime) -> bool:
    """Check if current time (with timezone) is within work hours."""

    start_hour, start_minute = map(int, WORK_HOURS_START.split(":"))
    end_hour, end_minute = map(int, WORK_HOURS_END.split(":"))

    current_time = now.time()
    start = time(start_hour, start_minute)
    end = time(end_hour, end_minute)

    if start < end:
        return start <= current_time < end

    # Work hours cross midnight (e.g. 22:00-06:00)
    return current_time >= start or current_time < end
