import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    PointHistoryItem,
    PointHistoryResponse,
    PointStatusEventItem,
    ReliabilitySummary,
)


@dataclass(frozen=True)
class ReliabilityAdjustment:
    adjustment: int
    reasons: list[str]
    warnings: list[str]


class ReliabilityService:
    def __init__(self, point_repository: PointRepository) -> None:
        self._point_repository = point_repository

    async def get_summary(
        self,
        *,
        country: str,
        name: str,
        days: int = 7,
    ) -> ReliabilitySummary:
        snapshots, events = await asyncio.gather(
            self._snapshots(country=country, name=name, days=days),
            self._events(country=country, name=name, days=days),
        )
        return build_reliability_summary(snapshots=snapshots, events=events)

    async def get_history(
        self,
        *,
        country: str,
        name: str,
        days: int = 7,
    ) -> PointHistoryResponse:
        snapshots, events = await asyncio.gather(
            self._snapshots(country=country, name=name, days=days),
            self._events(country=country, name=name, days=days),
        )
        reliability = build_reliability_summary(snapshots=snapshots, events=events)
        return PointHistoryResponse(
            country=country,
            name=name,
            window_days=days,
            reliability=reliability,
            timeline=[
                PointHistoryItem(
                    collected_at=_field(snapshot, "collectedAt"),
                    status=_field(snapshot, "status"),
                    locker_availability_status=_field(
                        snapshot,
                        "lockerAvailabilityStatus",
                    ),
                    score=_field(snapshot, "score") or 0,
                    grade=_field(snapshot, "grade") or "critical",
                )
                for snapshot in snapshots
            ],
            events=[
                PointStatusEventItem(
                    detected_at=_field(event, "detectedAt"),
                    event_type=_field(event, "eventType") or "unknown",
                    from_status=_field(event, "fromStatus"),
                    to_status=_field(event, "toStatus"),
                    from_locker_availability_status=_field(
                        event,
                        "fromLockerAvailabilityStatus",
                    ),
                    to_locker_availability_status=_field(
                        event,
                        "toLockerAvailabilityStatus",
                    ),
                )
                for event in events
            ],
        )

    async def _snapshots(self, *, country: str, name: str, days: int) -> list[Any]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return await self._point_repository.get_snapshots_since(
            country=country,
            name=name,
            since=since,
        )

    async def _events(self, *, country: str, name: str, days: int) -> list[Any]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return await self._point_repository.get_status_events_since(
            country=country,
            name=name,
            since=since,
        )


def build_reliability_summary(
    *,
    snapshots: list[Any],
    events: list[Any],
) -> ReliabilitySummary:
    snapshot_count = len(snapshots)
    status_changes = sum(
        1 for event in events if "status" in (_field(event, "eventType") or "")
    )
    operating_count = sum(1 for snapshot in snapshots if _field(snapshot, "status") == "Operating")
    uptime_ratio = operating_count / snapshot_count if snapshot_count > 0 else None
    last_problem_at = _last_problem_at(snapshots)
    latest_status = _field(snapshots[0], "status") if snapshots else None

    if snapshot_count < 2:
        label = "brak historii"
    elif latest_status and latest_status != "Operating":
        label = "problem"
    elif uptime_ratio is not None and uptime_ratio >= 0.98 and status_changes == 0:
        label = "stabilny"
    elif uptime_ratio is not None and uptime_ratio >= 0.9 and status_changes <= 2:
        label = "raczej stabilny"
    else:
        label = "niestabilny"

    return ReliabilitySummary(
        label=label,
        snapshot_count=snapshot_count,
        uptime_ratio=round(uptime_ratio, 3) if uptime_ratio is not None else None,
        status_changes=status_changes,
        last_problem_at=last_problem_at,
    )


def reliability_adjustment(summary: ReliabilitySummary) -> ReliabilityAdjustment:
    if summary.label == "brak historii":
        return ReliabilityAdjustment(
            adjustment=0,
            reasons=[],
            warnings=["Historia pojawi się po kilku uruchomieniach collectora"],
        )
    if summary.label == "stabilny":
        return ReliabilityAdjustment(
            adjustment=3,
            reasons=["Punkt był stabilny w ostatnich pomiarach"],
            warnings=[],
        )
    if summary.label == "raczej stabilny":
        return ReliabilityAdjustment(
            adjustment=1,
            reasons=["Historia punktu wygląda raczej stabilnie"],
            warnings=[],
        )
    if summary.label == "problem":
        return ReliabilityAdjustment(
            adjustment=-20,
            reasons=[],
            warnings=["Ostatni zapis historii wskazuje problem ze statusem"],
        )
    return ReliabilityAdjustment(
        adjustment=-10,
        reasons=[],
        warnings=["Historia pokazuje częste problemy albo zmiany statusu"],
    )


def _last_problem_at(snapshots: list[Any]) -> datetime | None:
    for snapshot in snapshots:
        if _field(snapshot, "status") != "Operating":
            return _field(snapshot, "collectedAt")
    return None


def _field(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)
