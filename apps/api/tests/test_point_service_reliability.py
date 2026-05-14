from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from locker_pulse_api.clients.inpost import InPostApiError
from locker_pulse_api.schemas import Coordinates, PointSummary
from locker_pulse_api.services.point_service import PointService


class FakeRepository:
    def __init__(self, snapshots, events, reports=None):
        self._snapshots = snapshots
        self._events = events
        self._reports = reports or []

    async def get_snapshots_since(self, **kwargs):
        return self._snapshots

    async def get_status_events_since(self, **kwargs):
        return self._events

    async def get_user_reports_since(self, **kwargs):
        return self._reports


class FailingInPostClient:
    async def get_point(self, **kwargs):
        raise InPostApiError("not found", status_code=404)


class CachedPointRepository(FakeRepository):
    async def get_point_record(self, **kwargs):
        return SimpleNamespace(
            raw={
                "country": "PL",
                "name": "SYZ01M",
                "status": "Operating",
                "location": {"latitude": 51.0808, "longitude": 22.4416},
                "address": {
                    "line1": "Strzyżewice 108",
                    "line2": "23-107 Strzyżewice",
                },
                "address_details": {
                    "city": "Strzyżewice",
                    "province": "lubelskie",
                    "post_code": "23-107",
                    "street": "Strzyżewice",
                    "building_number": "108",
                },
                "location_247": True,
                "easy_access_zone": True,
                "physical_type": "newfm",
                "image_url": None,
                "functions": ["parcel_collect", "parcel_send"],
                "locker_availability": {"status": "NO_DATA"},
                "demo_history": True,
            }
        )


def point_summary(score=90):
    return PointSummary(
        id="PL:WAW198M",
        name="WAW198M",
        country="PL",
        status="Operating",
        distance_m=100,
        address="Marszalkowska 1",
        city="Warszawa",
        province="mazowieckie",
        post_code="00-001",
        coordinates=Coordinates(lat=52.23, lng=21.01),
        score=score,
        grade="excellent",
        reasons=[],
        warnings=[],
        location_247=True,
        easy_access_zone=True,
        physical_type="newfm",
        image_url=None,
        functions=["parcel_collect"],
    )


@pytest.mark.asyncio
async def test_history_bonus_does_not_penalize_missing_history():
    service = PointService(None, FakeRepository(snapshots=[], events=[]))

    result = await service._apply_reliability_to_item(point_summary(score=90))

    assert result.score == 90
    assert result.history_adjustment == 0
    assert result.reliability.label == "brak historii"


@pytest.mark.asyncio
async def test_unstable_history_reduces_score():
    snapshots = [
        {"status": "Operating", "collectedAt": datetime.now(timezone.utc)},
        {"status": "Disabled", "collectedAt": datetime.now(timezone.utc)},
        {"status": "Operating", "collectedAt": datetime.now(timezone.utc)},
    ]
    events = [
        {"eventType": "status_changed", "detectedAt": datetime.now(timezone.utc)},
        {"eventType": "status_changed", "detectedAt": datetime.now(timezone.utc)},
        {"eventType": "status_changed", "detectedAt": datetime.now(timezone.utc)},
    ]
    service = PointService(None, FakeRepository(snapshots=snapshots, events=events))

    result = await service._apply_reliability_to_item(point_summary(score=90))

    assert result.score < 90
    assert result.history_adjustment < 0
    assert result.reliability.label == "niestabilny"


@pytest.mark.asyncio
async def test_ai_report_analysis_reduces_final_score():
    reports = [
        {
            "reason": "screen_problem",
            "createdAt": datetime.now(timezone.utc),
            "isDemo": False,
            "analysis": {
                "status": "ok",
                "severity": 80,
                "confidence": 0.8,
                "category": "screen_problem",
                "isActionable": True,
                "spamLikelihood": 0,
                "recommendedRiskFloor": "risky",
                "scorePenalty": 20,
                "photoEvidence": "strong",
                "summary": "Problem z ekranem.",
                "evidence": ["Komentarz wskazuje problem"],
                "modelName": "gemma3:4b",
                "promptVersion": "report-triage-v1",
                "createdAt": datetime.now(timezone.utc),
            },
        }
    ]
    service = PointService(None, FakeRepository(snapshots=[], events=[], reports=reports))

    result = await service._apply_reliability_to_item(point_summary(score=90))

    assert result.base_score == 90
    assert result.community_penalty == 20
    assert result.score == 70
    assert result.risk.level == "risky"


@pytest.mark.asyncio
async def test_point_detail_does_not_use_seeded_demo_cache():
    repository = CachedPointRepository(snapshots=[], events=[])
    service = PointService(FailingInPostClient(), repository)

    with pytest.raises(InPostApiError):
        await service.get_point(
            country="PL",
            name="SYZ01M",
            lat=51.0808,
            lng=22.4416,
            radius_m=3000,
        )