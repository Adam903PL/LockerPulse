from dataclasses import dataclass
from time import perf_counter

from locker_pulse_api.clients.inpost import InPostClient
from locker_pulse_api.repositories.point_repository import PointRepository


@dataclass(frozen=True)
class CollectorTarget:
    label: str
    lat: float | None
    lng: float | None
    radius_m: int | None
    country: str = "PL"
    point_type: str = "parcel_locker_only"
    max_pages: int = 1


@dataclass(frozen=True)
class CollectorSummary:
    collector_run_id: str | None
    status: str
    target_count: int
    point_count: int
    snapshot_count: int
    event_count: int
    duration_ms: int


class CollectorService:
    def __init__(self, inpost_client: InPostClient, point_repository: PointRepository) -> None:
        self._inpost_client = inpost_client
        self._point_repository = point_repository

    async def collect_once(
        self,
        *,
        targets: list[CollectorTarget],
        mode: str = "watchlist",
    ) -> CollectorSummary:
        started = perf_counter()
        collector_run_id = await self._point_repository.start_collector_run(
            mode=mode,
            target_count=len(targets),
        )
        seen: set[tuple[str, str]] = set()
        point_count = 0
        snapshot_count = 0
        event_count = 0

        try:
            for target in targets:
                items = await self._inpost_client.list_points(
                    country=target.country,
                    point_type=target.point_type,
                    per_page=100,
                    max_pages=target.max_pages,
                    lat=target.lat,
                    lng=target.lng,
                    radius_m=target.radius_m,
                )
                unique_items = []
                for item in items:
                    key = (item.get("country") or "", item.get("name") or "")
                    if not key[0] or not key[1] or key in seen:
                        continue
                    seen.add(key)
                    unique_items.append(item)

                result = await self._point_repository.save_points(
                    unique_items,
                    collector_run_id=collector_run_id,
                    record_snapshots=True,
                    radius_m=target.radius_m or 50_000,
                )
                point_count += result.point_count
                snapshot_count += result.snapshot_count
                event_count += result.event_count

            duration_ms = round((perf_counter() - started) * 1000)
            await self._point_repository.finish_collector_run(
                collector_run_id=collector_run_id,
                status="ok",
                point_count=point_count,
                snapshot_count=snapshot_count,
                event_count=event_count,
                duration_ms=duration_ms,
            )
            return CollectorSummary(
                collector_run_id=collector_run_id,
                status="ok",
                target_count=len(targets),
                point_count=point_count,
                snapshot_count=snapshot_count,
                event_count=event_count,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = round((perf_counter() - started) * 1000)
            await self._point_repository.finish_collector_run(
                collector_run_id=collector_run_id,
                status="error",
                point_count=point_count,
                snapshot_count=snapshot_count,
                event_count=event_count,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise
