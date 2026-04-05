from pydantic import BaseModel
import os


class SubAgentSettings(BaseModel):
    host: str = os.getenv("SUB_AGENT_HOST", "0.0.0.0")
    port: int = int(os.getenv("SUB_AGENT_PORT", "8001"))
    provider_type: str = os.getenv("PROVIDER_TYPE", "google")
    mcp_base_url: str = os.getenv("MCP_BASE_URL", "http://mcp_calendar_server:8002")
    request_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


settings = SubAgentSettings()
