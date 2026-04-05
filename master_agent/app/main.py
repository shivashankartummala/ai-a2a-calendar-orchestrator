from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .clients import SubAgentClient
from .config import settings
from .graph import run_orchestration
from .logging_config import configure_logging
from .models import WebhookRequest


configure_logging()
app = FastAPI(title="Master Calendar Orchestrator", version="1.0.0")
sub_agent_client = SubAgentClient(
    google_base_url=settings.google_agent_base_url,
    outlook_base_url=settings.outlook_agent_base_url,
    timeout=settings.request_timeout_seconds,
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/webhook/n8n")
async def n8n_webhook(payload: WebhookRequest) -> dict:
    if not payload.users:
        raise HTTPException(status_code=400, detail="users cannot be empty")

    result = await run_orchestration(
        input_request=payload.model_dump(),
        sub_agent_client=sub_agent_client,
    )
    return result
