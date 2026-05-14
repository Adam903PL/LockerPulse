from datetime import datetime, timedelta, timezone

import pytest

from locker_pulse_api.services.reliability import ReliabilityService
from locker_pulse_api.services.reliability import (
    build_reliability_summary,
    reliability_adjustment,
)


def snapshot(status="Operating", collected_at=None):
    return {
        "status": status,
        "collectedAt": collected_at or datetime.now(timezone.utc),
    }


def event(event_type="status_changed", detected_at=None):
    return {
        "eventType": event_type,
        "detectedAt": detected_at or datetime.now(timezone.utc),
    }


def test_reliability_without_snapshots_is_empty_history():
    summary = build_reliability_summary(snapshots=[], events=[])
    adjustment = reliability_adjustment(summary)

    assert summary.label == "brak historii"
    assert summary.snapshot_count == 0
    assert summary.uptime_ratio is None
    assert adjustment.adjustment == 0


def test_reliability_for_stable_operating_history_gets_small_bonus():
    summary = build_reliability_summary(
        snapshots=[snapshot(), snapshot(), snapshot()],
        events=[],
    )
    adjustment = reliability_adjustment(summary)

    assert summary.label == "stabilny"
    assert summary.uptime_ratio == 1.0
    assert adjustment.adjustment == 3


def test_reliability_detects_status_change_and_problem():
    problem_time = datetime.now(timezone.utc) - timedelta(hours=1)
    summary = build_reliability_summary(
        snapshots=[snapshot("Disabled", problem_time), snapshot("Operating")],
        events=[event()],
    )
    adjustment = reliability_adjustment(summary)

    assert summary.label == "problem"
    assert summary.status_changes == 1
    assert summary.last_problem_at == problem_time
    assert adjustment.adjustment == -20


def test_reliability_marks_unstable_history():
    summary = build_reliability_summary(
        snapshots=[
            snapshot("Operating"),
            snapshot("Disabled"),
            snapshot("Operating"),
            snapshot("Disabled"),
        ],
        events=[event(), event(), event()],
    )
    adjustment = reliability_adjustment(summary)

    assert summary.label in {"problem", "niestabilny"}
    assert adjustment.adjustment < 0


class FakeHistoryRepository:
    async def get_snapshots_since(self, **kwargs):
        return [
            {
                "status": "Operating",
                "collectedAt": datetime.now(timezone.utc),
                "lockerAvailabilityStatus": "NO_DATA",
                "score": 95,
                "grade": "excellent",
                "raw": {
                    "demo_history": True,
                    "demo_note": "Dane przykładowe do prezentacji panelu.",
                },
            },
            {
                "status": "Operating",
                "collectedAt": datetime.now(timezone.utc) - timedelta(days=1),
                "lockerAvailabilityStatus": "NO_DATA",
                "score": 95,
                "grade": "excellent",
                "raw": {"demo_history": True},
            },
        ]

    async def get_status_events_since(self, **kwargs):
        return []


@pytest.mark.asyncio
async def test_history_response_marks_demo_snapshots():
    service = ReliabilityService(FakeHistoryRepository())

    history = await service.get_history(country="PL", name="SYZ01M", days=7, include_demo=True)

    assert history.is_demo is True
    assert history.demo_note == "Dane przykładowe do prezentacji panelu."
