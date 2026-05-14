from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from locker_pulse_api.clients.geocoding import GeocodingClient, GeocodingError
from locker_pulse_api.config import get_settings
from locker_pulse_api.schemas import ApiErrorResponse, GeocodeResponse, GeocodeSuggestionsResponse
from locker_pulse_api.services.geocoding_service import GeocodingService

router = APIRouter(prefix="/api/v1/geocode", tags=["geocoding"])


def get_geocoding_service() -> GeocodingService:
    return GeocodingService(GeocodingClient(get_settings()))


@router.get("", response_model=GeocodeResponse, responses={404: {"model": ApiErrorResponse}})
async def geocode_address(
    q: Annotated[str, Query(min_length=3, max_length=240)],
    service: GeocodingService = Depends(get_geocoding_service),
) -> GeocodeResponse:
    try:
        return await service.geocode(q.strip())
    except GeocodingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/suggest", response_model=GeocodeSuggestionsResponse)
async def suggest_addresses(
    q: Annotated[str, Query(min_length=3, max_length=240)],
    limit: Annotated[int, Query(ge=1, le=8)] = 5,
    service: GeocodingService = Depends(get_geocoding_service),
) -> GeocodeSuggestionsResponse:
    try:
        return await service.suggest(q.strip(), limit=limit)
    except GeocodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
