from datetime import datetime, timezone
from typing import Any

from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    AdminDeleteReportResponse,
    AdminReportItem,
    AdminReportListResponse,
)
from locker_pulse_api.services.reports import analysis_to_public


class AdminReportNotFound(RuntimeError):
    pass


class AdminReportService:
    def __init__(self, point_repository: PointRepository) -> None:
        self._point_repository = point_repository

    async def list_reports(self, *, limit: int = 100, include_demo: bool = True) -> AdminReportListResponse:
        reports = await self._point_repository.list_user_reports(
            limit=limit,
            include_demo=include_demo,
        )
        items = [_to_admin_report_item(report) for report in reports]
        return AdminReportListResponse(count=len(items), items=items)

    async def delete_report(self, *, report_id: str) -> AdminDeleteReportResponse:
        deleted = await self._point_repository.delete_user_report(report_id=report_id)
        if not deleted:
            raise AdminReportNotFound(f"Report {report_id} not found.")
        return AdminDeleteReportResponse(deleted=True, report_id=report_id)


def _to_admin_report_item(report: Any) -> AdminReportItem:
    analysis = _field(report, "analysis")
    point = _field(report, "point")
    public_analysis = analysis_to_public(analysis)
    return AdminReportItem(
        id=_field(report, "id") or "",
        country=_field(report, "country") or "",
        name=_field(report, "name") or "",
        reason=_field(report, "reason") or "other",
        comment=_field(report, "comment") or "",
        photos_count=len(_report_photos(_field(report, "photos"))),
        source=_field(report, "source") or "web",
        is_demo=_field(report, "isDemo") is True,
        created_at=_field(report, "createdAt") or datetime.now(timezone.utc),
        point_address=_field(point, "address"),
        analysis_status=public_analysis.status if public_analysis else None,
        analysis=public_analysis,
    )


def _report_photos(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [photo for photo in value if isinstance(photo, dict)]


def _field(item: Any, name: str) -> Any:
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)
