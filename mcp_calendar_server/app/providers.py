from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from .tools import FetchCalendarSlotsOutput, TimeInterval, BookMeetingOutput


class MockCalendarBackend:
    def __init__(self) -> None:
        self.bookings: list[dict] = []

    @staticmethod
    def _today_at(hour: int, minute: int, tz: str = "America/Los_Angeles") -> datetime:
        now = datetime.now(ZoneInfo(tz))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def fetch_calendar_slots(self, user_id: str, provider: str) -> FetchCalendarSlotsOutput:
        # Deterministic mock busy slots used by both runtime and tests.
        base_tz = "America/Los_Angeles"
        day0_10 = self._today_at(10, 0, base_tz)
        day0_11 = self._today_at(11, 0, base_tz)
        day0_13 = self._today_at(13, 0, base_tz)
        day0_14 = self._today_at(14, 0, base_tz)

        mock_busy = {
            "A": [
                (day0_10, day0_11),
                (day0_13, day0_14),
            ],
            "B": [
                (day0_10 + timedelta(minutes=30), day0_11 + timedelta(minutes=30)),
            ],
            "C": [
                (day0_11, day0_13),
            ],
        }

        intervals = [
            TimeInterval(start_time=start, end_time=end)
            for start, end in mock_busy.get(user_id, [])
        ]

        return FetchCalendarSlotsOutput(
            user_id=user_id,
            provider=provider,
            timezone=base_tz,
            busy=intervals,
        )

    def book_meeting(
        self,
        start_time: datetime,
        end_time: datetime,
        attendees: list[str],
        provider: str = "mock",
    ) -> BookMeetingOutput:
        meeting_id = f"mock-{uuid4()}"
        self.bookings.append(
            {
                "meeting_id": meeting_id,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
                "provider": provider,
            }
        )

        return BookMeetingOutput(
            booked=True,
            meeting_id=meeting_id,
            provider=provider,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
        )
