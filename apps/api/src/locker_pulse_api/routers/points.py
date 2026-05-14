from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from locker_pulse_api.clients.inpost import InPostApiError, InPostClient
from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    ApiErrorResponse,
    PointAlternativesResponse,
    PointSearchResponse,
    PointSummary,
)
from locker_pulse_api.services.point_service import PointService

router = APIRouter(prefix="/api/v1/points", tags=["points"])


def get_point_service(request: Request) -> PointService:
    settings = get_settings()
    repository = getattr(request.app.state, "point_repository", PointRepository(None))
    return PointService(InPostClient(settings), repository)


@router.get(
    "/search",
    response_model=PointSearchResponse,
    responses={502: {"model": ApiErrorResponse}},
)
async def search_points(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=100, le=50_000)] = 3000,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    country: Annotated[str, Query(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")] = "PL",
    point_type: Annotated[str, Query(alias="type", min_length=1, max_length=64)] = "parcel_locker_only",
    functions: Annotated[list[str] | None, Query()] = None,
    open_24_7: bool | None = None,
    easy_access: bool | None = None,
    min_score: Annotated[int | None, Query(ge=0, le=100)] = None,
    demo: bool = False,
    service: PointService = Depends(get_point_service),
) -> PointSearchResponse:
    try:
        return await service.search(
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            limit=limit,
            country=country,
            point_type=point_type,
            functions=_normalize_functions(functions),
            open_24_7=open_24_7,
            easy_access=easy_access,
            min_score=min_score,
            demo=demo,
        )
    except InPostApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/{country}/{name}/alternatives",
    response_model=PointAlternativesResponse,
    responses={502: {"model": ApiErrorResponse}},
)
async def get_point_alternatives(
    country: Annotated[str, Path(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")],
    name: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=500, le=50_000)] = 3000,
    limit: Annotated[int, Query(ge=1, le=3)] = 3,
    demo: bool = False,
    service: PointService = Depends(get_point_service),
) -> PointAlternativesResponse:
    try:
        return await service.get_alternatives(
            country=country,
            name=name,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            limit=limit,
            demo=demo,
        )
    except InPostApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/{country}/{name}",
    response_model=PointSummary,
    responses={502: {"model": ApiErrorResponse}},
)
async def get_point(
    country: Annotated[str, Path(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")],
    name: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_m: Annotated[int, Query(ge=100, le=50_000)] = 3000,
    demo: bool = False,
    service: PointService = Depends(get_point_service),
) -> PointSummary:
    try:
        return await service.get_point(
            country=country,
            name=name,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            demo=demo,
        )
    except InPostApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _normalize_functions(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    for value in values:
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned:
                normalized.append(cleaned)
    return sorted(set(normalized))
