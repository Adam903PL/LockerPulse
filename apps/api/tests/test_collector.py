import pytest

from locker_pulse_api.repositories.point_repository import SavePointsResult
from locker_pulse_api.services.collector_service import CollectorService, CollectorTarget


class FakeInPostClient:
    async def list_points(self, **kwargs):
        return [
            {"country": "PL", "name": "WAW01M", "status": "Operating"},
            {"country": "PL", "name": "WAW01M", "status": "Operating"},
            {"country": "PL", "name": "WAW02M", "status": "Disabled"},
        ]


class FakePointRepository:
    def __init__(self):
        self.started = False
        self.finished = None
        self.saved_points = []

    async def start_collector_run(self, **kwargs):
        self.started = True
        assert kwargs["mode"] == "watchlist"
        assert kwargs["target_count"] == 1
        return "run-1"

    async def save_points(self, points, **kwargs):
        self.saved_points.extend(points)
        assert kwargs["collector_run_id"] == "run-1"
        assert kwargs["record_snapshots"] is True
        return SavePointsResult(point_count=len(points), snapshot_count=len(points), event_count=1)

    async def finish_collector_run(self, **kwargs):
        self.finished = kwargs


@pytest.mark.asyncio
async def test_collector_deduplicates_points_and_logs_summary():
    repository = FakePointRepository()
    service = CollectorService(FakeInPostClient(), repository)

    summary = await service.collect_once(
        targets=[
            CollectorTarget(
                label="Warszawa",
                lat=52.2297,
                lng=21.0122,
                radius_m=3000,
            )
        ],
    )

    assert repository.started is True
    assert len(repository.saved_points) == 2
    assert summary.point_count == 2
    assert summary.snapshot_count == 2
    assert summary.event_count == 1
    assert repository.finished["status"] == "ok"
