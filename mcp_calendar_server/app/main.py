from __future__ import annotations

import logging
from fastapi import FastAPI, HTTPException

from .config import settings
from .providers import CalendarBackend
from .tools import (
    MCP_TOOL_DEFINITIONS,
    BookMeetingInput,
    BookMeetingOutput,
    FetchCalendarSlotsInput,
    FetchCalendarSlotsOutput,
)

app = FastAPI(title="OpenMCP Calendar Server", version="1.0.0")
logger = logging.getLogger("mcp_calendar_server")
backend = CalendarBackend()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "mock_mode": settings.mock_mode}


@app.get("/tools")
def tools() -> dict:
    return {"tools": MCP_TOOL_DEFINITIONS}


@app.post("/tools/fetch_calendar_slots", response_model=FetchCalendarSlotsOutput)
def fetch_calendar_slots(payload: FetchCalendarSlotsInput) -> FetchCalendarSlotsOutput:
    logger.info(
        "mcp.fetch_calendar_slots",
        extra={"user_id": payload.user_id, "provider": payload.provider},
    )
    try:
        return backend.fetch_calendar_slots(user_id=payload.user_id, provider=payload.provider)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/tools/book_meeting", response_model=BookMeetingOutput)
def book_meeting(payload: BookMeetingInput) -> BookMeetingOutput:
    logger.info(
        "mcp.book_meeting",
        extra={"attendees": payload.attendees, "start_time": payload.start_time.isoformat()},
    )
    provider = "google"
    for attendee in payload.attendees:
        if attendee.lower().endswith(("@outlook.com", "@hotmail.com", "@live.com", "@microsoft.com")):
            provider = "outlook"
            break

    try:
        return backend.book_meeting(
            start_time=payload.start_time,
            end_time=payload.end_time,
            attendees=payload.attendees,
            provider=provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
