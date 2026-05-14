from typing import Any

import httpx

from locker_pulse_api.config import Settings


class GeocodingError(RuntimeError):
    pass


class GeocodingClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.nominatim_api_base_url.rstrip("/")
        self._timeout = settings.inpost_request_timeout_seconds

    async def search(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": limit,
            "countrycodes": "pl",
        }
        headers = {
            "User-Agent": "LockerPulse/0.1 (technical-assignment; local-development)",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=headers,
            ) as client:
                response = await client.get("/search", params=params)
                response.raise_for_status()
                results = response.json()
        except httpx.HTTPError as exc:
            raise GeocodingError("Geocoding request failed") from exc

        if not isinstance(results, list):
            raise GeocodingError("Geocoding response was invalid")

        return results

    async def geocode(self, query: str) -> dict[str, Any]:
        results = await self.search(query, limit=1)
        if not results:
            raise GeocodingError("Address was not found")

        return results[0]
