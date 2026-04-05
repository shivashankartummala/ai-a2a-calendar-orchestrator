from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


Provider = Literal["google", "outlook"]


class FetchCalendarSlotsInput(BaseModel):
    user_id: str = Field(..., description="User identifier, e.g., A/B/C")
    provider: Provider = Field(..., description="Calendar provider: google or outlook")


class TimeInterval(BaseModel):
    start_time: datetime
    end_time: datetime


class FetchCalendarSlotsOutput(BaseModel):
    user_id: str
    provider: Provider
    timezone: str
    busy: list[TimeInterval]


class BookMeetingInput(BaseModel):
    start_time: datetime
    end_time: datetime
    attendees: list[str]


class BookMeetingOutput(BaseModel):
    booked: bool
    meeting_id: str
    provider: str
    start_time: datetime
    end_time: datetime
    attendees: list[str]


MCP_TOOL_DEFINITIONS = [
    {
        "name": "fetch_calendar_slots",
        "description": "Fetch busy slots for a specific user and provider.",
        "input_schema": FetchCalendarSlotsInput.model_json_schema(),
        "output_schema": FetchCalendarSlotsOutput.model_json_schema(),
    },
    {
        "name": "book_meeting",
        "description": "Book a meeting for attendees at an agreed time.",
        "input_schema": BookMeetingInput.model_json_schema(),
        "output_schema": BookMeetingOutput.model_json_schema(),
    },
]
