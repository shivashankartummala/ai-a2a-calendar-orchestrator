from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from dateutil.parser import isoparse
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")
    return dt


def _normalize(slots: list[dict]) -> list[tuple[datetime, datetime]]:
    intervals = []
    for slot in slots:
        start = _ensure_aware(isoparse(slot["start_time"]))
        end = _ensure_aware(isoparse(slot["end_time"]))
        if end > start:
            intervals.append((start.astimezone(UTC), end.astimezone(UTC)))
    intervals.sort(key=lambda x: x[0])
    return intervals


def _ceil_to_slot(dt: datetime, slot_minutes: int) -> datetime:
    dt = _ensure_aware(dt)
    slot_seconds = slot_minutes * 60
    epoch_seconds = int(dt.timestamp())
    remainder = epoch_seconds % slot_seconds
    if remainder == 0:
        return dt
    return datetime.fromtimestamp(epoch_seconds + (slot_seconds - remainder), tz=dt.tzinfo)


def _intersect_two(
    left: list[tuple[datetime, datetime]],
    right: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    i = 0
    j = 0
    result: list[tuple[datetime, datetime]] = []

    while i < len(left) and j < len(right):
        s1, e1 = left[i]
        s2, e2 = right[j]

        start = max(s1, s2)
        end = min(e1, e2)
        if end > start:
            result.append((start, end))

        if e1 <= e2:
            i += 1
        else:
            j += 1

    return result


def find_first_shared_slot(
    free_by_user: dict[str, list[dict]],
    duration_minutes: int = 30,
    slot_granularity_minutes: int = 30,
    horizon_days: int = 7,
    now: Optional[datetime] = None,
) -> Optional[dict]:
    if not free_by_user:
        return None

    cursor = _ensure_aware(now if now else datetime.now(UTC)).astimezone(UTC)
    horizon_end = cursor + timedelta(days=horizon_days)

    users = sorted(free_by_user.keys())
    common = _normalize(free_by_user[users[0]])

    for user in users[1:]:
        common = _intersect_two(common, _normalize(free_by_user[user]))
        if not common:
            return None

    needed = timedelta(minutes=duration_minutes)
    for start, end in common:
        bounded_start = max(start, cursor)
        bounded_end = min(end, horizon_end)
        candidate_start = _ceil_to_slot(bounded_start, slot_granularity_minutes)
        if bounded_end - candidate_start >= needed:
            return {
                "start_time": candidate_start.isoformat(),
                "end_time": (candidate_start + needed).isoformat(),
            }

    return None
