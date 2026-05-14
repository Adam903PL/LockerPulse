from typing import Any

import httpx

from locker_pulse_api.config import Settings


INPOST_FIELDS = ",".join(
    [
        "country",
        "name",
        "type",
        "status",
        "location",
        "distance",
        "address",
        "address_details",
        "location_description",
        "opening_hours",
        "functions",
        "location_247",
        "easy_access_zone",
        "physical_type",
        "image_url",
        "locker_availability",
        "unavailability_periods",
    ]
)


class InPostApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InPostClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.inpost_api_base_url.rstrip("/")
        self._timeout = settings.inpost_request_timeout_seconds

    async def search_points(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: int,
        country: str,
        point_type: str,
        per_page: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "relative_point": f"{lat},{lng}",
            "max_distance": radius_m,
            "sort_by": "distance_to_relative_point",
            "country": country,
            "type": point_type,
            "per_page": min(max(per_page, 1), 100),
            "page": 1,
            "fields": INPOST_FIELDS,
        }
        return await self._get("points", params=params)

    async def list_points(
        self,
        *,
        country: str,
        point_type: str,
        per_page: int = 100,
        max_pages: int = 1,
        lat: float | None = None,
        lng: float | None = None,
        radius_m: int | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            params: dict[str, Any] = {
                "country": country,
                "type": point_type,
                "per_page": min(max(per_page, 1), 100),
                "page": page,
                "fields": INPOST_FIELDS,
            }
            if lat is not None and lng is not None:
                params["relative_point"] = f"{lat},{lng}"
                params["sort_by"] = "distance_to_relative_point"
            if radius_m is not None:
                params["max_distance"] = radius_m

            payload = await self._get("points", params=params)
            page_items = payload.get("items") or []
            items.extend(page_items)
            if len(page_items) < params["per_page"]:
                break
            page += 1
        return items

    async def get_point(self, *, country: str, name: str) -> dict[str, Any]:
        return await self._get(f"points/{country}/{name}", params={"fields": INPOST_FIELDS})

    async def _get(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise InPostApiError(
                f"InPost API returned HTTP {exc.response.status_code}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise InPostApiError("InPost API request failed") from exc
