from __future__ import annotations

import httpx


class SubAgentClient:
    def __init__(self, google_base_url: str, outlook_base_url: str, timeout: float = 10.0) -> None:
        self.google_base_url = google_base_url.rstrip("/")
        self.outlook_base_url = outlook_base_url.rstrip("/")
        self.timeout = timeout

    def _base_url_for_provider(self, provider: str) -> str:
        if provider == "google":
            return self.google_base_url
        if provider == "outlook":
            return self.outlook_base_url
        raise ValueError(f"Unsupported provider: {provider}")

    async def get_availability(self, trace_id: str, user_id: str, provider: str) -> dict:
        payload = {
            "trace_id": trace_id,
            "user_id": user_id,
            "provider": provider,
            "horizon_days": 7,
        }
        base_url = self._base_url_for_provider(provider)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{base_url}/availability", json=payload)
            response.raise_for_status()
            return response.json()

    async def book_as_admin(
        self,
        trace_id: str,
        provider: str,
        start_time: str,
        end_time: str,
        attendees: list[str],
    ) -> dict:
        payload = {
            "trace_id": trace_id,
            "provider": provider,
            "requested_by": "A",
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
        }
        base_url = self._base_url_for_provider(provider)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{base_url}/book", json=payload)
            response.raise_for_status()
            return response.json()
