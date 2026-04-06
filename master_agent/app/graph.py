from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from litellm import acompletion

from .clients import SubAgentClient
from .config import settings
from .models import OrchestratorState
from .scheduler import find_first_shared_slot


logger = logging.getLogger("master_agent")


async def _parse_request(state: OrchestratorState) -> OrchestratorState:
    request = state["request"]
    trace_id = state["trace_id"]
    users = request["users"]
    requested_providers = request.get("providers", {}) or {}

    provider = "google"
    if settings.use_llm_planner:
        response = await acompletion(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "Return JSON with {provider}. Choose google or outlook.",
                },
                {
                    "role": "user",
                    "content": json.dumps(request),
                },
            ],
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        provider = parsed.get("provider", "google")

    logger.info(
        "master.parse_request",
        extra={"trace_id": trace_id, "event": "parse_request", "user_id": "-"},
    )
    provider_by_user = {user_id: requested_providers.get(user_id, provider) for user_id in users}
    return {"provider": provider, "provider_by_user": provider_by_user}


async def _request_availability(state: OrchestratorState, sub_agent_client: SubAgentClient) -> OrchestratorState:
    request = state["request"]
    trace_id = state["trace_id"]
    provider = state.get("provider", "google")
    provider_by_user = state.get("provider_by_user", {})
    users = request["users"]

    logger.info(
        "master.availability.broadcast",
        extra={"trace_id": trace_id, "event": "availability_broadcast", "user_id": "-"},
    )

    tasks = [
        sub_agent_client.get_availability(
            trace_id=trace_id,
            user_id=user_id,
            provider=provider_by_user.get(user_id, provider),
        )
        for user_id in users
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    by_user: dict[str, dict] = {}
    failures: dict[str, str] = {}

    for user_id, result in zip(users, responses):
        if isinstance(result, Exception):
            failures[user_id] = str(result)
            continue
        by_user[user_id] = result

    logger.info(
        "master.availability.collected",
        extra={"trace_id": trace_id, "event": "availability_collected", "user_id": "-"},
    )

    if failures:
        return {
            "sub_agent_results": by_user,
            "availability_failures": failures,
            "status": "availability_failed",
            "error": "One or more user calendars could not be queried.",
        }

    return {"sub_agent_results": by_user, "availability_failures": {}}


async def _negotiate_slot(state: OrchestratorState) -> OrchestratorState:
    trace_id = state["trace_id"]
    if state.get("status") == "availability_failed":
        return {"status": "availability_failed", "proposed_slot": None}

    results = state.get("sub_agent_results", {})
    free_by_user = {u: payload["free"] for u, payload in results.items()}

    slot = find_first_shared_slot(free_by_user=free_by_user, duration_minutes=30, horizon_days=7)

    logger.info(
        "master.negotiate_slot",
        extra={"trace_id": trace_id, "event": "negotiate_slot", "user_id": "-"},
    )

    if slot is None:
        return {"status": "no_shared_slot", "proposed_slot": None}

    return {"status": "slot_found", "proposed_slot": slot}


async def _book_if_possible(state: OrchestratorState, sub_agent_client: SubAgentClient) -> OrchestratorState:
    trace_id = state["trace_id"]
    request = state["request"]
    status = state.get("status")
    slot = state.get("proposed_slot")
    provider_by_user = state.get("provider_by_user", {})
    admin_provider = provider_by_user.get("A", state.get("provider", "google"))
    user_emails = request.get("user_emails", {})

    if status == "availability_failed":
        return {"booking_result": None, "status": "availability_failed"}
    if status == "no_shared_slot":
        return {"booking_result": None, "status": "no_shared_slot"}
    if status != "slot_found" or not slot:
        return {"booking_result": None, "status": "failed"}

    attendees = [user_emails.get(user_id, user_id) for user_id in request["users"]]

    booking = await sub_agent_client.book_as_admin(
        trace_id=trace_id,
        provider=admin_provider,
        start_time=slot["start_time"],
        end_time=slot["end_time"],
        attendees=attendees,
    )

    logger.info(
        "master.booking.completed",
        extra={"trace_id": trace_id, "event": "booking_completed", "user_id": "A"},
    )

    return {"booking_result": booking, "status": "success"}


def build_graph(sub_agent_client: SubAgentClient):
    graph = StateGraph(OrchestratorState)

    async def request_availability_node(state: OrchestratorState) -> OrchestratorState:
        return await _request_availability(state, sub_agent_client)

    async def book_if_possible_node(state: OrchestratorState) -> OrchestratorState:
        return await _book_if_possible(state, sub_agent_client)

    graph.add_node("parse_request", _parse_request)
    graph.add_node("request_availability", request_availability_node)
    graph.add_node("negotiate_slot", _negotiate_slot)
    graph.add_node("book_if_possible", book_if_possible_node)

    graph.add_edge(START, "parse_request")
    graph.add_edge("parse_request", "request_availability")
    graph.add_edge("request_availability", "negotiate_slot")
    graph.add_edge("negotiate_slot", "book_if_possible")
    graph.add_edge("book_if_possible", END)

    return graph.compile()


async def run_orchestration(input_request: dict, sub_agent_client: SubAgentClient) -> dict:
    trace_id = str(uuid4())
    app = build_graph(sub_agent_client)
    initial: OrchestratorState = {
        "trace_id": trace_id,
        "request": input_request,
        "status": "started",
        "error": None,
    }

    result = await app.ainvoke(initial)
    return {
        "trace_id": trace_id,
        "status": result.get("status", "failed"),
        "error": result.get("error"),
        "availability_failures": result.get("availability_failures", {}),
        "proposed_slot": result.get("proposed_slot"),
        "booking_result": result.get("booking_result"),
    }
