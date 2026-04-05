from pydantic import BaseModel
import os


class MasterSettings(BaseModel):
    host: str = os.getenv("MASTER_HOST", "0.0.0.0")
    port: int = int(os.getenv("MASTER_PORT", "8000"))
    google_agent_base_url: str = os.getenv("GOOGLE_AGENT_BASE_URL", "http://google_agent_service:8001")
    outlook_agent_base_url: str = os.getenv("OUTLOOK_AGENT_BASE_URL", "http://outlook_agent_service:8001")
    llm_model: str = os.getenv("LITELLM_MODEL", "claude-3-5-sonnet-20241022")
    use_llm_planner: bool = os.getenv("USE_LLM_PLANNER", "false").lower() == "true"
    request_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


settings = MasterSettings()
