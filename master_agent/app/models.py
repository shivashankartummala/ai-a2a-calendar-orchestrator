from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, TypedDict
from pydantic import BaseModel, Field


class WebhookRequest(BaseModel):
    trigger: str = Field(..., examples=["email"])
    topic: str = Field(..., examples=["security"])
    users: list[str] = Field(..., examples=[["A", "B", "C"]])
    user_emails: dict[str, str] = Field(
        default_factory=dict,
        description="Optional map of user id to attendee email, e.g. {'A':'a@gmail.com'}",
    )
    providers: dict[str, Literal["google", "outlook"]] = Field(
        default_factory=dict,
        description="Optional per-user provider map, e.g. {'A':'google','B':'outlook','C':'google'}",
    )


class MeetingWindow(BaseModel):
    start_time: datetime
    end_time: datetime


class OrchestratorState(TypedDict, total=False):
    trace_id: str
    request: dict
    provider: str
    provider_by_user: dict[str, str]
    sub_agent_results: dict
    availability_failures: dict[str, str]
    proposed_slot: Optional[dict]
    booking_result: Optional[dict]
    status: str
    error: Optional[str]
