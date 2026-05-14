from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query, Request, status

from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    ApiErrorResponse,
    ReportAnalysisResponse,
    ReportSummary,
    UserReportCreate,
    UserReportResponse,
)
from locker_pulse_api.services.report_triage import ReportTriageService
from locker_pulse_api.services.report_triage_engines import build_report_triage_engine
from locker_pulse_api.services.reports import ReportPointNotFound, ReportService

router = APIRouter(prefix="/api/v1/points", tags=["reports"])
analysis_router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def get_report_service(request: Request) -> ReportService:
    settings = get_settings()
    repository = getattr(request.app.state, "point_repository", PointRepository(None))
    return ReportService(
        repository,
        model_name=settings.report_triage_model or "rules",
        prompt_version=settings.report_triage_prompt_version,
    )


def get_report_triage_service(request: Request) -> ReportTriageService:
    settings = get_settings()
    repository = getattr(request.app.state, "point_repository", PointRepository(None))
    return ReportTriageService(
        point_repository=repository,
        triage_engine=build_report_triage_engine(
            provider=settings.report_triage_provider,
            model_name=settings.report_triage_model,
            api_base=settings.effective_report_triage_api_base,
            timeout_seconds=settings.report_triage_timeout_seconds,
            allow_cloud_photos=settings.report_triage_allow_cloud_photos,
            local_model_prefixes=settings.triage_local_model_prefixes,
        ),
        prompt_version=settings.report_triage_prompt_version,
    )


@router.get("/{country}/{name}/reports/summary", response_model=ReportSummary)
async def get_report_summary(
    country: Annotated[str, Path(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")],
    name: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    service: ReportService = Depends(get_report_service),
) -> ReportSummary:
    return await service.get_summary(country=country, name=name, days=days)


@router.post(
    "/{country}/{name}/reports",
    response_model=UserReportResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ApiErrorResponse}},
)
async def create_report(
    country: Annotated[str, Path(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")],
    name: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")],
    payload: UserReportCreate,
    background_tasks: BackgroundTasks,
    service: ReportService = Depends(get_report_service),
    triage_service: ReportTriageService = Depends(get_report_triage_service),
) -> UserReportResponse:
    try:
        response = await service.create_report(country=country, name=name, payload=payload)
    except ReportPointNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background_tasks.add_task(triage_service.analyze_report, report_id=response.id)
    return response


@analysis_router.get("/{report_id}/analysis", response_model=ReportAnalysisResponse)
async def get_report_analysis(
    report_id: Annotated[str, Path(min_length=1, max_length=128)],
    service: ReportTriageService = Depends(get_report_triage_service),
) -> ReportAnalysisResponse:
    return ReportAnalysisResponse(
        report_id=report_id,
        analysis=await service.get_public_analysis(report_id=report_id),
    )
