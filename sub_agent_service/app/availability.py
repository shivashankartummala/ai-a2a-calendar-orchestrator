from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from dateutil.parser import isoparse


UTC = ZoneInfo("UTC")


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")
    return dt


def _clamp_interval(
    start: datetime,
    end: datetime,
    min_dt: datetime,
    max_dt: datetime,
) -> Optional[Tuple[datetime, datetime]]:
    s = max(start, min_dt)
    e = min(end, max_dt)
    if s >= e:
        return None
    return s, e


def busy_to_free(
    busy_intervals: list[dict],
    timezone: str,
    horizon_start: datetime,
    horizon_end: datetime,
    workday_start_hour: int = 9,
    workday_end_hour: int = 17,
) -> list[dict]:
    horizon_start = _ensure_aware(horizon_start).astimezone(UTC)
    horizon_end = _ensure_aware(horizon_end).astimezone(UTC)
    tz = ZoneInfo(timezone)

    busy: list[tuple[datetime, datetime]] = []
    for item in busy_intervals:
        s = _ensure_aware(isoparse(item["start_time"]))
        e = _ensure_aware(isoparse(item["end_time"]))
        if e > s:
            busy.append((s.astimezone(UTC), e.astimezone(UTC)))

    busy.sort(key=lambda x: x[0])

    free: list[tuple[datetime, datetime]] = []
    day_cursor = horizon_start.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    last_day = horizon_end.astimezone(tz).date()

    while day_cursor.date() <= last_day:
        work_start_local = day_cursor.replace(hour=workday_start_hour)
        work_end_local = day_cursor.replace(hour=workday_end_hour)
        day_cursor += timedelta(days=1)

        work_start = work_start_local.astimezone(UTC)
        work_end = work_end_local.astimezone(UTC)
        bounded = _clamp_interval(work_start, work_end, horizon_start, horizon_end)
        if not bounded:
            continue

        cursor_start, cursor_end = bounded
        current = cursor_start

        for b_start, b_end in busy:
            if b_end <= current:
                continue
            if b_start >= cursor_end:
                break
            if b_start > current:
                free.append((current, min(b_start, cursor_end)))
            current = max(current, b_end)
            if current >= cursor_end:
                break

        if current < cursor_end:
            free.append((current, cursor_end))

    return [
        {"start_time": start.isoformat(), "end_time": end.isoformat()}
        for start, end in free
        if end > start
    ]
