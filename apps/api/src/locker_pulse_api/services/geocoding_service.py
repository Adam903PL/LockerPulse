from locker_pulse_api.clients.geocoding import GeocodingClient, GeocodingError
from typing import Any

from locker_pulse_api.schemas import (
    Coordinates,
    GeocodeResponse,
    GeocodeSuggestion,
    GeocodeSuggestionsResponse,
)


class GeocodingService:
    def __init__(self, geocoding_client: GeocodingClient) -> None:
        self._geocoding_client = geocoding_client

    async def geocode(self, query: str) -> GeocodeResponse:
        result = await self._geocoding_client.geocode(query)
        return GeocodeResponse(
            query=query,
            **self._parse_result(result, query).model_dump(),
        )

    async def suggest(self, query: str, limit: int) -> GeocodeSuggestionsResponse:
        results = await self._geocoding_client.search(query, limit=limit)
        suggestions: list[GeocodeSuggestion] = []
        for result in results:
            try:
                suggestions.append(self._parse_result(result, query))
            except GeocodingError:
                continue

        return GeocodeSuggestionsResponse(
            query=query,
            count=len(suggestions),
            items=suggestions,
        )

    def _parse_result(self, result: dict[str, Any], fallback_name: str) -> GeocodeSuggestion:
        try:
            lat = float(result["lat"])
            lng = float(result["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GeocodingError("Geocoding response did not contain coordinates") from exc

        return GeocodeSuggestion(
            display_name=result.get("display_name") or fallback_name,
            coordinates=Coordinates(lat=lat, lng=lng),
        )
