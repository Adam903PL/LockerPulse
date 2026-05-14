from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import PointHistoryResponse
from locker_pulse_api.services.reliability import ReliabilityService

router = APIRouter(prefix="/api/v1/points", tags=["history"])


def get_reliability_service(request: Request) -> ReliabilityService:
    repository = getattr(request.app.state, "point_repository", PointRepository(None))
    return ReliabilityService(repository)


@router.get("/{country}/{name}/history", response_model=PointHistoryResponse)
async def get_point_history(
    country: Annotated[str, Path(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")],
    name: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    service: ReliabilityService = Depends(get_reliability_service),
) -> PointHistoryResponse:
    return await service.get_history(country=country, name=name, days=days)
