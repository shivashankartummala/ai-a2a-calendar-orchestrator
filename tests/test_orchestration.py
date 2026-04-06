from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from master_agent.app.graph import run_orchestration


UTC = ZoneInfo("UTC")


class FakeSubAgentClient:
    def __init__(self, availabilities: dict[str, list[dict]]) -> None:
        self.availabilities = availabilities
        self.booking_calls: list[dict] = []
        self.availability_calls: list[dict] = []

    async def get_availability(self, trace_id: str, user_id: str, provider: str) -> dict:
        self.availability_calls.append(
            {
                "trace_id": trace_id,
                "user_id": user_id,
                "provider": provider,
            }
        )
        return {
            "trace_id": trace_id,
            "user_id": user_id,
            "provider": provider,
            "timezone": "UTC",
            "busy": [],
            "free": self.availabilities[user_id],
        }

    async def book_as_admin(
        self,
        trace_id: str,
        provider: str,
        start_time: str,
        end_time: str,
        attendees: list[str],
    ) -> dict:
        self.booking_calls.append(
            {
                "trace_id": trace_id,
                "provider": provider,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
            }
        )
        return {
            "booked": True,
            "meeting_id": "mock-test-1",
            "provider": "mock",
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
        }


class FailingSubAgentClient(FakeSubAgentClient):
    async def get_availability(self, trace_id: str, user_id: str, provider: str) -> dict:
        if user_id == "B":
            raise RuntimeError("MCP availability failed for user_id=B: missing calendar permissions")
        return await super().get_availability(trace_id, user_id, provider)


@pytest.mark.asyncio
async def test_success_path_books_meeting() -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=2)

    slots = [{"start_time": start.isoformat(), "end_time": end.isoformat()}]
    client = FakeSubAgentClient(availabilities={"A": slots, "B": slots, "C": slots})

    result = await run_orchestration(
        input_request={"trigger": "email", "topic": "security", "users": ["A", "B", "C"]},
        sub_agent_client=client,
    )

    assert result["status"] == "success"
    assert result["booking_result"]["booked"] is True
    assert len(client.booking_calls) == 1
    assert client.booking_calls[0]["provider"] == "google"


@pytest.mark.asyncio
async def test_failure_path_no_shared_slot() -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    a_start = now + timedelta(hours=1)
    b_start = now + timedelta(hours=3)
    c_start = now + timedelta(hours=5)

    client = FakeSubAgentClient(
        availabilities={
            "A": [{"start_time": a_start.isoformat(), "end_time": (a_start + timedelta(minutes=45)).isoformat()}],
            "B": [{"start_time": b_start.isoformat(), "end_time": (b_start + timedelta(minutes=45)).isoformat()}],
            "C": [{"start_time": c_start.isoformat(), "end_time": (c_start + timedelta(minutes=45)).isoformat()}],
        }
    )

    result = await run_orchestration(
        input_request={"trigger": "email", "topic": "security", "users": ["A", "B", "C"]},
        sub_agent_client=client,
    )

    assert result["status"] == "no_shared_slot"
    assert result["proposed_slot"] is None
    assert result["booking_result"] is None
    assert client.booking_calls == []


@pytest.mark.asyncio
async def test_mixed_provider_map_routes_per_user() -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=2)
    slots = [{"start_time": start.isoformat(), "end_time": end.isoformat()}]

    client = FakeSubAgentClient(availabilities={"A": slots, "B": slots, "C": slots})
    provider_map = {"A": "google", "B": "outlook", "C": "google"}

    result = await run_orchestration(
        input_request={
            "trigger": "email",
            "topic": "security",
            "users": ["A", "B", "C"],
            "providers": provider_map,
        },
        sub_agent_client=client,
    )

    called_map = {c["user_id"]: c["provider"] for c in client.availability_calls}
    assert result["status"] == "success"
    assert called_map == provider_map
    assert client.booking_calls[0]["provider"] == "google"


@pytest.mark.asyncio
async def test_availability_failure_returns_structured_error() -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=2)
    slots = [{"start_time": start.isoformat(), "end_time": end.isoformat()}]

    client = FailingSubAgentClient(availabilities={"A": slots, "B": slots, "C": slots})
    result = await run_orchestration(
        input_request={
            "trigger": "email",
            "topic": "security",
            "users": ["A", "B", "C"],
            "providers": {"A": "google", "B": "google", "C": "google"},
        },
        sub_agent_client=client,
    )

    assert result["status"] == "availability_failed"
    assert result["booking_result"] is None
    assert result["proposed_slot"] is None
    assert "B" in result["availability_failures"]
    assert client.booking_calls == []
