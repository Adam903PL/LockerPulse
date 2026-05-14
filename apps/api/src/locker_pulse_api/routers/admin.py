from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status

from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    AdminDeleteReportResponse,
    AdminReportListResponse,
    ApiErrorResponse,
)
from locker_pulse_api.services.admin_reports import AdminReportNotFound, AdminReportService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def verify_admin_token(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    token = get_settings().admin_token
    if not token:
        return
    if x_admin_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token.")


def get_admin_report_service(request: Request) -> AdminReportService:
    repository = getattr(request.app.state, "point_repository", PointRepository(None))
    return AdminReportService(repository)


@router.get(
    "/reports",
    response_model=AdminReportListResponse,
    responses={401: {"model": ApiErrorResponse}},
)
async def list_reports(
    _: Annotated[None, Depends(verify_admin_token)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    include_demo: bool = True,
    service: AdminReportService = Depends(get_admin_report_service),
) -> AdminReportListResponse:
    return await service.list_reports(limit=limit, include_demo=include_demo)


@router.delete(
    "/reports/{report_id}",
    response_model=AdminDeleteReportResponse,
    responses={401: {"model": ApiErrorResponse}, 404: {"model": ApiErrorResponse}},
)
async def delete_report(
    report_id: Annotated[str, Path(min_length=1, max_length=128)],
    _: Annotated[None, Depends(verify_admin_token)],
    service: AdminReportService = Depends(get_admin_report_service),
) -> AdminDeleteReportResponse:
    try:
        return await service.delete_report(report_id=report_id)
    except AdminReportNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
