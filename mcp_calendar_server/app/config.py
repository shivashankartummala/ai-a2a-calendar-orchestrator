from pydantic import BaseModel
import os


class MCPSettings(BaseModel):
    host: str = os.getenv("MCP_HOST", "0.0.0.0")
    port: int = int(os.getenv("MCP_PORT", "8002"))
    mock_mode: bool = os.getenv("MCP_MOCK_MODE", "true").lower() == "true"


settings = MCPSettings()
