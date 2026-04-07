from __future__ import annotations

import json
import ast
from datetime import datetime, timedelta
from typing import Dict, Tuple
from urllib.parse import quote
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

from .config import settings
from .tools import FetchCalendarSlotsOutput, TimeInterval, BookMeetingOutput


class MockCalendarBackend:
    def __init__(self) -> None:
        self.bookings: list[dict] = []

    @staticmethod
    def _today_at(hour: int, minute: int, tz: str = "America/Los_Angeles") -> datetime:
        now = datetime.now(ZoneInfo(tz))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def fetch_calendar_slots(self, user_id: str, provider: str) -> FetchCalendarSlotsOutput:
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


class GoogleCalendarBackend:
    def __init__(self) -> None:
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.token_uri = settings.google_token_uri
        self.default_timezone = settings.google_default_timezone
        self.booking_user_id = settings.google_booking_user_id
        self.fallback_calendar_id = settings.google_fallback_calendar_id
        self.fallback_refresh_token = settings.google_fallback_refresh_token
        self.user_config = self._parse_user_config(settings.google_user_config_json)

    @staticmethod
    def _parse_user_config(raw: str) -> Dict[str, Dict[str, str]]:
        normalized_raw = (raw or "{}").strip()
        try:
            parsed = json.loads(normalized_raw)
        except json.JSONDecodeError as exc:
            try:
                # Fallback for env values serialized as Python-style dict strings.
                parsed = ast.literal_eval(normalized_raw)
            except Exception:
                raise ValueError("GOOGLE_USER_CONFIG_JSON is not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise ValueError("GOOGLE_USER_CONFIG_JSON must be a JSON object")

        normalized: Dict[str, Dict[str, str]] = {}
        for user_id, data in parsed.items():
            if not isinstance(data, dict):
                continue
            calendar_id = str(data.get("calendar_id", "primary"))
            refresh_token = str(data.get("refresh_token", ""))
            email = str(data.get("email", ""))
            normalized[str(user_id)] = {
                "calendar_id": calendar_id,
                "refresh_token": refresh_token,
                "email": email,
            }
        return normalized

    def _require_google_enabled(self) -> None:
        if not self.client_id or not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set for live Google mode")

    def _user_credentials(self, user_id: str) -> Tuple[str, str, str]:
        user = self.user_config.get(user_id, {})
        email = user.get("email") or ""
        raw_calendar_id = user.get("calendar_id") or self.fallback_calendar_id
        # If calendar_id is left as "primary" for non-admin shared calendars, prefer the explicit email id.
        calendar_id = email if (raw_calendar_id == "primary" and user_id != self.booking_user_id and email) else raw_calendar_id
        refresh_token = user.get("refresh_token") or self.fallback_refresh_token
        if not refresh_token and self.booking_user_id in self.user_config:
            refresh_token = self.user_config[self.booking_user_id].get("refresh_token", "")
        if not refresh_token:
            raise ValueError(f"No refresh token configured for user_id={user_id}")
        return calendar_id, refresh_token, email

    def _refresh_access_token(self, refresh_token: str) -> str:
        self._require_google_enabled()
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(self.token_uri, data=payload)
            response.raise_for_status()
            token_response = response.json()
        access_token = token_response.get("access_token")
        if not access_token:
            raise ValueError("Google OAuth token response missing access_token")
        return access_token

    def fetch_calendar_slots(self, user_id: str, provider: str) -> FetchCalendarSlotsOutput:
        if provider != "google":
            raise ValueError(f"Live mode currently supports google only, got provider={provider}")

        calendar_id, refresh_token, _ = self._user_credentials(user_id)
        access_token = self._refresh_access_token(refresh_token)

        now = datetime.now(ZoneInfo("UTC"))
        horizon = now + timedelta(days=14)

        body = {
            "timeMin": now.isoformat(),
            "timeMax": horizon.isoformat(),
            "timeZone": self.default_timezone,
            "items": [{"id": calendar_id}],
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client(timeout=20.0) as client:
            response = client.post("https://www.googleapis.com/calendar/v3/freeBusy", json=body, headers=headers)
            response.raise_for_status()
            payload = response.json()

        busy_raw = payload.get("calendars", {}).get(calendar_id, {}).get("busy", [])
        busy = [
            TimeInterval(start_time=item["start"], end_time=item["end"])
            for item in busy_raw
            if "start" in item and "end" in item
        ]
        return FetchCalendarSlotsOutput(
            user_id=user_id,
            provider="google",
            timezone=self.default_timezone,
            busy=busy,
        )

    def book_meeting(
        self,
        start_time: datetime,
        end_time: datetime,
        attendees: list[str],
        provider: str = "google",
    ) -> BookMeetingOutput:
        if provider != "google":
            raise ValueError(f"Live mode currently supports google only, got provider={provider}")

        calendar_id, refresh_token, admin_email = self._user_credentials(self.booking_user_id)
        access_token = self._refresh_access_token(refresh_token)
        headers = {"Authorization": f"Bearer {access_token}"}

        attendee_emails = [a for a in attendees if "@" in a]
        if admin_email and admin_email not in attendee_emails:
            attendee_emails.append(admin_email)

        body = {
            "summary": "A2A Scheduled Meeting",
            "start": {"dateTime": start_time.isoformat(), "timeZone": self.default_timezone},
            "end": {"dateTime": end_time.isoformat(), "timeZone": self.default_timezone},
            "attendees": [{"email": email} for email in attendee_emails],
        }

        encoded_calendar = quote(calendar_id, safe="")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar}/events"

        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, params={"sendUpdates": "all"}, json=body, headers=headers)
            response.raise_for_status()
            event = response.json()

        return BookMeetingOutput(
            booked=True,
            meeting_id=event.get("id", ""),
            provider="google",
            start_time=start_time,
            end_time=end_time,
            attendees=attendee_emails,
        )


class CalendarBackend:
    def __init__(self) -> None:
        self.mock = MockCalendarBackend()
        self.google = GoogleCalendarBackend()

    def fetch_calendar_slots(self, user_id: str, provider: str) -> FetchCalendarSlotsOutput:
        if settings.mock_mode:
            return self.mock.fetch_calendar_slots(user_id=user_id, provider=provider)
        return self.google.fetch_calendar_slots(user_id=user_id, provider=provider)

    def book_meeting(self, start_time: datetime, end_time: datetime, attendees: list[str], provider: str) -> BookMeetingOutput:
        if settings.mock_mode:
            return self.mock.book_meeting(start_time=start_time, end_time=end_time, attendees=attendees, provider="mock")
        return self.google.book_meeting(
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            provider=provider,
        )
