from __future__ import annotations

import httpx


class MCPClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def fetch_calendar_slots(self, user_id: str, provider: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/tools/fetch_calendar_slots",
                json={"user_id": user_id, "provider": provider},
            )
            response.raise_for_status()
            return response.json()

    async def book_meeting(self, start_time: str, end_time: str, attendees: list[str]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/tools/book_meeting",
                json={"start_time": start_time, "end_time": end_time, "attendees": attendees},
            )
            response.raise_for_status()
            return response.json()
