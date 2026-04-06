from __future__ import annotations

import logging
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel
from zoneinfo import ZoneInfo
from datetime import timezone

from .availability import busy_to_free
from .config import settings
from .mcp_client import MCPClient



class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
            "user_id": getattr(record, "user_id", "-"),
        }
        return json.dumps(payload)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
root = logging.getLogger()
root.handlers = [handler]
root.setLevel(logging.INFO)

logger = logging.getLogger("sub_agent_service")

app = FastAPI(title=f"{settings.provider_type.title()} Agent Service", version="1.0.0")
mcp_client = MCPClient(base_url=settings.mcp_base_url, timeout=settings.request_timeout_seconds)
UTC = ZoneInfo("UTC")


class AvailabilityRequest(BaseModel):
    trace_id: str
    user_id: str
    provider: Optional[str] = None
    horizon_days: int = 7


class BookingRequest(BaseModel):
    trace_id: str
    provider: Optional[str] = None
    requested_by: str
    start_time: datetime
    end_time: datetime
    attendees: list[str]


@app.get("/health")
def health() -> dict:
    return {"ok": True, "provider": settings.provider_type}


@app.post("/availability")
async def availability(req: AvailabilityRequest) -> dict:
    logger.info("sub_agent.availability.request", extra={"trace_id": req.trace_id, "user_id": req.user_id})
    requested_provider = req.provider or settings.provider_type
    if requested_provider != settings.provider_type:
        raise HTTPException(
            status_code=400,
            detail=f"Provider mismatch for this agent. expected={settings.provider_type} requested={requested_provider}",
        )

    try:
        slots = await mcp_client.fetch_calendar_slots(user_id=req.user_id, provider=settings.provider_type)
    except httpx.HTTPStatusError as exc:
        detail = f"MCP availability failed for user_id={req.user_id}: {exc.response.text}"
        raise HTTPException(status_code=424, detail=detail)
    now = datetime.now(UTC)
    horizon_end = now + timedelta(days=req.horizon_days)

    free_slots = busy_to_free(
        busy_intervals=slots["busy"],
        timezone=slots["timezone"],
        horizon_start=now,
        horizon_end=horizon_end,
    )

    payload = {
        "trace_id": req.trace_id,
        "user_id": req.user_id,
        "provider": settings.provider_type,
        "timezone": slots["timezone"],
        "busy": slots["busy"],
        "free": free_slots,
    }

    logger.info("sub_agent.availability.response", extra={"trace_id": req.trace_id, "user_id": req.user_id})
    return payload


@app.post("/book")
async def book(req: BookingRequest) -> dict:
    logger.info("sub_agent.booking.request", extra={"trace_id": req.trace_id, "user_id": req.requested_by})
    requested_provider = req.provider or settings.provider_type
    if requested_provider != settings.provider_type:
        raise HTTPException(
            status_code=400,
            detail=f"Provider mismatch for this agent. expected={settings.provider_type} requested={requested_provider}",
        )

    if req.requested_by != "A":
        raise HTTPException(status_code=403, detail="Only admin user A can trigger booking")

    booking = await mcp_client.book_meeting(
        start_time=req.start_time.isoformat(),
        end_time=req.end_time.isoformat(),
        attendees=req.attendees,
    )
    logger.info("sub_agent.booking.success", extra={"trace_id": req.trace_id, "user_id": req.requested_by})
    return booking
