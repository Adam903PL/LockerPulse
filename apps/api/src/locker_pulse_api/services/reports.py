from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    ReportRiskFloor,
    ReportSummary,
    UserReportAnalysisPublic,
    UserReportCreate,
    UserReportResponse,
)


REASON_LABELS = {
    "not_working": "Paczkomat nie działa",
    "full": "Brak miejsca",
    "screen_problem": "Problem z ekranem",
    "access_problem": "Problem z dostępem",
    "other": "Inny problem",
}


class ReportPointNotFound(RuntimeError):
    pass


class ReportService:
    def __init__(
        self,
        point_repository: PointRepository,
        *,
        model_name: str = "rules",
        prompt_version: str = "report-triage-v1",
    ) -> None:
        self._point_repository = point_repository
        self._model_name = model_name
        self._prompt_version = prompt_version

    async def create_report(
        self,
        *,
        country: str,
        name: str,
        payload: UserReportCreate,
        is_demo: bool = False,
    ) -> UserReportResponse:
        report = await self._point_repository.create_user_report(
            country=country,
            name=name,
            reason=payload.reason,
            comment=payload.comment.strip(),
            photos=[photo.model_dump() for photo in payload.photos],
            lat=payload.lat,
            lng=payload.lng,
            source="web",
            is_demo=is_demo,
        )
        if report is None:
            raise ReportPointNotFound(f"Point {country}:{name} is not available in local cache.")

        report_id = _field(report, "id") or ""
        if report_id:
            await self._point_repository.create_report_analysis_pending(
                report_id=report_id,
                model_name=self._model_name,
                prompt_version=self._prompt_version,
            )

        summary = await self.get_summary(country=country, name=name, days=7, include_demo=is_demo)
        return UserReportResponse(
            id=report_id,
            country=country,
            name=name,
            reason=_field(report, "reason") or payload.reason,
            comment=_field(report, "comment") or payload.comment,
            photos=_report_photos(_field(report, "photos")),
            source=_field(report, "source") or "web",
            is_demo=_field(report, "isDemo") is True,
            created_at=_field(report, "createdAt") or datetime.now(timezone.utc),
            summary=summary,
            analysis_status="pending",
        )

    async def get_summary(
        self,
        *,
        country: str,
        name: str,
        days: int = 7,
        include_demo: bool = False,
    ) -> ReportSummary:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        reports = await self._point_repository.get_user_reports_since(
            country=country,
            name=name,
            since=since,
            include_demo=include_demo,
        )
        return build_report_summary(reports=reports, days=days)


def build_report_summary(*, reports: list[Any], days: int = 7) -> ReportSummary:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    count_24h = sum(1 for report in reports if _created_at(report) >= day_ago)
    reason_counts = Counter(_field(report, "reason") or "other" for report in reports)
    latest_report_at = _created_at(reports[0]) if reports else None
    stats = _analysis_stats(reports=reports, since=day_ago)
    signal, label, message = _classify_report_signal(
        count_24h,
        ai_risk_floor=stats["ai_risk_floor"],
        analysis_count=stats["analysis_count"],
        community_penalty=stats["community_penalty"],
        pending_count=stats["analysis_pending_count"],
    )

    return ReportSummary(
        signal=signal,
        label=label,
        message=message,
        count_24h=count_24h,
        count_window=len(reports),
        window_days=days,
        reasons=dict(reason_counts),
        latest_report_at=latest_report_at,
        has_demo_data=any(_field(report, "isDemo") is True for report in reports),
        analysis_count=stats["analysis_count"],
        analysis_pending_count=stats["analysis_pending_count"],
        problem_score_24h=stats["problem_score_24h"],
        max_severity_24h=stats["max_severity_24h"],
        community_penalty=stats["community_penalty"],
        ai_risk_floor=stats["ai_risk_floor"],
        analysis_provider=stats["analysis_provider"],
        analysis_mode=stats["analysis_mode"],
        analysis_model=stats["analysis_model"],
    )


def calculate_score_penalty(
    *,
    severity: int,
    confidence: float,
    category: str,
    spam_likelihood: float,
    is_actionable: bool,
) -> int:
    if (
        severity < 25
        or confidence < 0.35
        or category == "spam"
        or spam_likelihood >= 0.8
        or not is_actionable
    ):
        return 0
    if severity <= 45:
        return 5
    if severity <= 65:
        return 10
    if severity <= 85:
        return 20
    return 30


def analysis_to_public(analysis: Any | None) -> UserReportAnalysisPublic | None:
    if analysis is None:
        return None
    return UserReportAnalysisPublic(
        status=_field(analysis, "status") or "pending",
        severity=_field(analysis, "severity") or 0,
        confidence=_field(analysis, "confidence") or 0,
        category=_field(analysis, "category") or "unclear",
        is_actionable=_field(analysis, "isActionable") is True,
        spam_likelihood=_field(analysis, "spamLikelihood") or 0,
        photo_evidence=_field(analysis, "photoEvidence") or "none",
        recommended_risk_floor=_field(analysis, "recommendedRiskFloor") or "none",
        score_penalty=_field(analysis, "scorePenalty") or 0,
        summary=_field(analysis, "summary") or "Analiza oczekuje na wynik.",
        evidence=_json_list(_field(analysis, "evidence")),
        model_name=_field(analysis, "modelName") or "",
        prompt_version=_field(analysis, "promptVersion") or "",
        provider=_field(analysis, "provider") or "rules",
        analysis_mode=_field(analysis, "analysisMode") or "rules",
        used_images=_field(analysis, "usedImages") is True,
        created_at=_field(analysis, "createdAt") or datetime.now(timezone.utc),
        finished_at=_field(analysis, "finishedAt"),
        error=_field(analysis, "error"),
    )


def _classify_report_signal(
    count_24h: int,
    *,
    ai_risk_floor: ReportRiskFloor,
    analysis_count: int,
    community_penalty: int,
    pending_count: int,
) -> tuple[str, str, str]:
    if analysis_count > 0 and community_penalty > 0:
        if ai_risk_floor == "critical":
            return (
                "heavy",
                "Wysoki problem w zgłoszeniach",
                "Świeże zgłoszenia wyglądają na poważny problem. Warto wybrać Plan B.",
            )
        if ai_risk_floor == "risky":
            return (
                "multiple",
                "Średni problem w zgłoszeniach",
                "Świeże zgłoszenia wyglądają na realne ryzyko dla tego punktu.",
            )
        return (
            "recent",
            "Lekki problem w zgłoszeniach",
            "Świeże zgłoszenia sugerują problem, ale nie wygląda on krytycznie.",
        )
    if pending_count > 0 and count_24h > 0:
        return (
            "recent",
            "Analiza zgłoszenia w toku",
            "Zgłoszenie zapisane. System ocenia, jak mocno powinno wpłynąć na rekomendację.",
        )
    if count_24h >= 4:
        return (
            "heavy",
            "Dużo zgłoszeń dzisiaj",
            "Kilku użytkowników zgłosiło dziś problem z tym punktem.",
        )
    if count_24h >= 2:
        return (
            "multiple",
            "Kilka zgłoszeń dzisiaj",
            "Ten punkt ma kilka świeżych zgłoszeń problemu.",
        )
    if count_24h == 1:
        return (
            "recent",
            "Ostatnio zgłaszano problem",
            "Ktoś niedawno zgłosił problem z tym punktem.",
        )
    return (
        "none",
        "Brak zgłoszeń",
        "Nie ma świeżych zgłoszeń problemu dla tego punktu.",
    )


def _analysis_stats(*, reports: list[Any], since: datetime) -> dict[str, Any]:
    analyses = [
        _field(report, "analysis")
        for report in reports
        if _created_at(report) >= since and _field(report, "analysis") is not None
    ]
    pending_count = sum(1 for analysis in analyses if _field(analysis, "status") in {"pending", "failed"})
    ok_analyses = [analysis for analysis in analyses if _field(analysis, "status") == "ok"]
    valid = [
        analysis
        for analysis in ok_analyses
        if _field(analysis, "isActionable") is True
        and (_field(analysis, "confidence") or 0) >= 0.35
        and (_field(analysis, "category") or "") != "spam"
        and (_field(analysis, "spamLikelihood") or 0) < 0.8
    ]

    if not valid:
        latest_analysis = _latest_analysis(analyses)
        return {
            "analysis_count": len(ok_analyses),
            "analysis_pending_count": pending_count,
            "problem_score_24h": 0,
            "max_severity_24h": 0,
            "community_penalty": 0,
            "ai_risk_floor": "none",
            "analysis_provider": _field(latest_analysis, "provider"),
            "analysis_mode": _field(latest_analysis, "analysisMode"),
            "analysis_model": _field(latest_analysis, "modelName"),
        }

    latest_analysis = _latest_analysis(ok_analyses)
    penalties = [_field(analysis, "scorePenalty") or 0 for analysis in valid]
    weighted_scores = [
        int(round((_field(analysis, "severity") or 0) * (_field(analysis, "confidence") or 0)))
        for analysis in valid
    ]
    average_penalty = round(sum(penalties) / len(penalties))
    volume_bonus = min(10, len(valid) * 2)
    community_penalty = min(35, average_penalty + volume_bonus)

    return {
        "analysis_count": len(ok_analyses),
        "analysis_pending_count": pending_count,
        "problem_score_24h": round(sum(weighted_scores) / len(weighted_scores)),
        "max_severity_24h": max(_field(analysis, "severity") or 0 for analysis in valid),
        "community_penalty": community_penalty,
        "ai_risk_floor": _highest_risk_floor(
            [_field(analysis, "recommendedRiskFloor") or "none" for analysis in valid]
        ),
        "analysis_provider": _field(latest_analysis, "provider"),
        "analysis_mode": _field(latest_analysis, "analysisMode"),
        "analysis_model": _field(latest_analysis, "modelName"),
    }


def _latest_analysis(analyses: list[Any]) -> Any | None:
    if not analyses:
        return None
    empty_date = datetime.min.replace(tzinfo=timezone.utc)
    return max(analyses, key=lambda analysis: _field(analysis, "createdAt") or empty_date)


def _highest_risk_floor(values: list[str]) -> ReportRiskFloor:
    order = {
        "none": 0,
        "watch": 1,
        "risky": 2,
        "critical": 3,
    }
    selected = max(values, key=lambda value: order.get(value, 0), default="none")
    if selected in {"watch", "risky", "critical"}:
        return selected  # type: ignore[return-value]
    return "none"


def _created_at(report: Any) -> datetime:
    value = _field(report, "createdAt")
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _field(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _report_photos(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [photo for photo in value if isinstance(photo, dict)]


def _json_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
