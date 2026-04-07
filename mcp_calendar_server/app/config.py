from pydantic import BaseModel
import os


class MCPSettings(BaseModel):
    host: str = os.getenv("MCP_HOST", "0.0.0.0")
    port: int = int(os.getenv("MCP_PORT", "8002"))
    mock_mode: bool = os.getenv("MCP_MOCK_MODE", "true").lower() == "true"
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_token_uri: str = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
    google_user_config_json: str = os.getenv("GOOGLE_USER_CONFIG_JSON", "{}")
    google_fallback_calendar_id: str = os.getenv("GOOGLE_FALLBACK_CALENDAR_ID", "primary")
    google_fallback_refresh_token: str = os.getenv(
        "GOOGLE_FALLBACK_REFRESH_TOKEN",
        os.getenv("GOOGLE_REFRESH_TOKEN", ""),
    )
    google_booking_user_id: str = os.getenv("GOOGLE_BOOKING_USER_ID", "A")
    google_default_timezone: str = os.getenv("GOOGLE_DEFAULT_TIMEZONE", "UTC")


settings = MCPSettings()
