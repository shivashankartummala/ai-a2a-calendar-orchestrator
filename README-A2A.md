In this project, the Agent-to-Agent (A2A) protocol is implemented as a structured pattern of task delegation and message exchange between a central orchestrator and specialized sub-agents. Instead of a single service handling all calendar types, the system splits responsibilities across agents that "negotiate" to reach a shared goal.

The A2A protocol is used across two primary phases of the scheduling workflow:

1. Asynchronous Availability Discovery
The Master Agent initiates a "broadcast" to multiple sub-agents to discover when users are free:

Role Specialization: The Master Agent identifies which sub-agent service (Google or Outlook) is responsible for each user.

Standardized Messaging: The Master Agent sends a uniform POST /availability request to each sub-agent.

Protocol Contract: Each sub-agent is responsible for its own user's data; it fetches raw intervals from the MCP server, calculates free time, and returns a standardized JSON object to the Master Agent.

Decoupled Logic: The Master Agent does not need to know how to calculate "free time" from "busy time"; it simply trusts the sub-agent's response.

2. Admin Booking Delegation
Once a shared slot is identified by the Master Agent's internal scheduler, the protocol dictates how the booking is finalized:

Admin Path: The protocol identifies User A as the admin who has the authority to book the meeting.

Command Delegation: Instead of the Master Agent booking the meeting directly, it sends a POST /book command to the Admin's Sub-Agent.

Guardrail Enforcement: The sub-agent validates that the request is coming from the authorized admin (User A) before calling the final MCP tool to book the meeting.

3. Technical Implementation Details
The "protocol" itself is enforced through several architectural choices:

Traceable Negotiation: A unique trace_id is passed in every A2A request, allowing the entire multi-agent conversation to be traced across different service logs.

HTTP/JSON Contract: The protocol uses FastAPI to define strict request and response models, ensuring that agents can always "understand" each other regardless of their internal implementation.

Service Discovery: The Master Agent uses base URLs for the Google and Outlook services to route A2A messages to the correct provider agent.

By using this A2A pattern, the system remains highly modular; you can add a third sub-agent for a different provider (like Apple Calendar) without changing the core negotiation logic in the Master Agent.