# A2A Protocol Walkthrough

This project implements the Agent-to-Agent (A2A) protocol as a structured pattern of task delegation and message exchange between:

1. A central `master_agent` (orchestrator)
2. Specialized provider agents (`google_agent_service`, `outlook_agent_service`)
3. A shared MCP tool server (`mcp_calendar_server`)

Instead of one service handling everything, agents collaborate to negotiate a shared scheduling outcome.

## Why This Is A2A

The system demonstrates core A2A properties:

1. Role specialization: each agent has a focused responsibility.
2. Standardized inter-agent contracts: agents communicate using consistent HTTP/JSON payloads.
3. Delegated execution: the master coordinates, but does not perform provider-specific operations itself.
4. Negotiation traceability: each interaction carries `trace_id` for end-to-end visibility.

## Phase 1: Asynchronous Availability Discovery

The `master_agent` starts a broadcast-style discovery across provider agents.

### Flow

1. Master identifies the responsible provider agent for each user.
2. Master sends standardized `POST /availability` requests.
3. Each provider agent:
4. Fetches raw busy intervals from MCP (`fetch_calendar_slots`).
5. Converts busy intervals to free intervals.
6. Returns standardized free/busy JSON to the master.

### A2A Characteristics

1. `master_agent` does not compute provider-specific calendar extraction logic.
2. Provider agents are independently replaceable.
3. Availability calculation remains encapsulated per agent.

## Phase 2: Admin Booking Delegation

After shared-slot intersection, booking is delegated through the admin path.

### Flow

1. Master selects a shared candidate slot.
2. Protocol identifies user `A` as booking authority.
3. Master sends `POST /book` to the admin's provider agent.
4. Provider agent validates admin guardrail (`requested_by == "A"`).
5. Provider agent invokes MCP `book_meeting`.

### A2A Characteristics

1. Authority stays with the sub-agent boundary, not hardcoded in master-side booking logic.
2. Final booking execution is delegated, not centralized.

## Protocol Contracts And Enforcement

The protocol is enforced through concrete engineering choices:

1. `trace_id` propagation across all A2A calls.
2. FastAPI request/response models for strict schema contracts.
3. Provider-based service routing using configured base URLs.
4. Guardrails in provider agents for provider mismatch and admin authorization.

## Modularity And Extensibility

Because negotiation logic is separated from provider execution:

1. You can add a new provider agent (for example Apple Calendar) with minimal master changes.
2. Existing provider agents remain unaffected.
3. The master orchestration and intersection logic can stay stable while integrations evolve.
