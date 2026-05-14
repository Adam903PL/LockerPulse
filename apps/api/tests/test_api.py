from datetime import datetime, timezone

from fastapi.testclient import TestClient

from locker_pulse_api.main import app
from locker_pulse_api.routers.admin import get_admin_report_service
from locker_pulse_api.routers.geocode import get_geocoding_service
from locker_pulse_api.routers.history import get_reliability_service
from locker_pulse_api.routers.points import get_point_service
from locker_pulse_api.routers.reports import get_report_service, get_report_triage_service


class FakePointService:
    async def search(self, **kwargs):
        from locker_pulse_api.schemas import (
            Coordinates,
            PointSearchResponse,
            PointSummary,
            SearchInsights,
            SearchQueryEcho,
        )

        return PointSearchResponse(
            query=SearchQueryEcho(
                lat=kwargs["lat"],
                lng=kwargs["lng"],
                radius_m=kwargs["radius_m"],
                country=kwargs["country"],
                type=kwargs["point_type"],
                functions=kwargs["functions"],
                open_24_7=kwargs["open_24_7"],
                easy_access=kwargs["easy_access"],
                min_score=kwargs["min_score"],
            ),
            count=1,
            upstream_count=1,
            items=[
                PointSummary(
                    id="PL:WAW198M",
                    name="WAW198M",
                    country="PL",
                    status="Operating",
                    distance_m=124,
                    address="Marszalkowska 1, 00-001 Warszawa",
                    city="Warszawa",
                    province="mazowieckie",
                    post_code="00-001",
                    coordinates=Coordinates(lat=52.23, lng=21.01),
                    score=95,
                    grade="excellent",
                    reasons=["Operating"],
                    warnings=["Źródłowe API zwraca locker_availability=NO_DATA"],
                    location_247=True,
                    easy_access_zone=True,
                    physical_type="newfm",
                    image_url=None,
                    functions=["parcel_collect"],
                )
            ],
            insights=SearchInsights(operating=1, availability_no_data=1, open_24_7=1, easy_access=1),
        )

    async def get_point(self, **kwargs):
        from locker_pulse_api.schemas import Coordinates, PointSummary

        assert kwargs["country"] == "PL"
        assert kwargs["name"] == "WAW198M"
        assert kwargs["lat"] == 52.2297
        assert kwargs["lng"] == 21.0122
        assert kwargs["radius_m"] == 3000

        return PointSummary(
            id="PL:WAW198M",
            name="WAW198M",
            country="PL",
            status="Operating",
            distance_m=124,
            address="Marszalkowska 1, 00-001 Warszawa",
            city="Warszawa",
            province="mazowieckie",
            post_code="00-001",
            coordinates=Coordinates(lat=52.23, lng=21.01),
            score=95,
            grade="excellent",
            reasons=["Punkt działa poprawnie"],
            warnings=[],
            location_247=True,
            easy_access_zone=True,
            physical_type="newfm",
            image_url=None,
            functions=["parcel_collect"],
        )

    async def get_alternatives(self, **kwargs):
        from locker_pulse_api.schemas import (
            Coordinates,
            PointAlternativesResponse,
            PointRisk,
            PointSummary,
        )

        risk = PointRisk(
            level="critical",
            label="Krytyczny",
            message="Ten punkt może być dziś problematyczny.",
            reasons=["Status punktu jest niedostępny"],
        )
        point = PointSummary(
            id="PL:WAW198M",
            name="WAW198M",
            country="PL",
            status="Disabled",
            distance_m=124,
            address="Marszalkowska 1, 00-001 Warszawa",
            city="Warszawa",
            province="mazowieckie",
            post_code="00-001",
            coordinates=Coordinates(lat=52.23, lng=21.01),
            score=20,
            grade="critical",
            reasons=[],
            warnings=[],
            location_247=True,
            easy_access_zone=True,
            physical_type="newfm",
            image_url=None,
            functions=["parcel_collect"],
            risk=risk,
        )
        alternative = point.model_copy(
            update={
                "id": "PL:WAW200M",
                "name": "WAW200M",
                "status": "Operating",
                "distance_m": 260,
                "score": 94,
                "grade": "excellent",
                "risk": PointRisk(
                    level="ok",
                    label="Stabilny",
                    message="Wygląda na dobry wybór.",
                    reasons=[],
                ),
            }
        )
        return PointAlternativesResponse(
            point=point,
            risk=risk,
            alternatives=[alternative],
            message="Najlepsza alternatywa w pobliżu to WAW200M.",
        )


def override_service():
    return FakePointService()


class FakeGeocodingService:
    async def geocode(self, query):
        from locker_pulse_api.schemas import Coordinates, GeocodeResponse

        return GeocodeResponse(
            query=query,
            display_name="Dluga 1, Gdansk, Polska",
            coordinates=Coordinates(lat=54.351, lng=18.646),
        )

    async def suggest(self, query, limit):
        from locker_pulse_api.schemas import (
            Coordinates,
            GeocodeSuggestion,
            GeocodeSuggestionsResponse,
        )

        return GeocodeSuggestionsResponse(
            query=query,
            count=2,
            items=[
                GeocodeSuggestion(
                    display_name="Dluga 1, Gdansk, Polska",
                    coordinates=Coordinates(lat=54.351, lng=18.646),
                ),
                GeocodeSuggestion(
                    display_name="Dluga 2, Gdansk, Polska",
                    coordinates=Coordinates(lat=54.352, lng=18.647),
                ),
            ][:limit],
        )


def override_geocoding_service():
    return FakeGeocodingService()


class FakeReliabilityService:
    async def get_history(self, **kwargs):
        from locker_pulse_api.schemas import (
            PointHistoryItem,
            PointHistoryResponse,
            PointStatusEventItem,
            ReliabilitySummary,
        )

        now = datetime.now(timezone.utc)
        return PointHistoryResponse(
            country=kwargs["country"],
            name=kwargs["name"],
            window_days=kwargs["days"],
            reliability=ReliabilitySummary(
                label="stabilny",
                snapshot_count=2,
                uptime_ratio=1.0,
                status_changes=0,
                last_problem_at=None,
            ),
            timeline=[
                PointHistoryItem(
                    collected_at=now,
                    status="Operating",
                    locker_availability_status="NO_DATA",
                    score=95,
                    grade="excellent",
                )
            ],
            events=[
                PointStatusEventItem(
                    detected_at=now,
                    event_type="status_changed",
                    from_status="Disabled",
                    to_status="Operating",
                    from_locker_availability_status="NO_DATA",
                    to_locker_availability_status="NO_DATA",
                )
            ],
        )


def override_reliability_service():
    return FakeReliabilityService()


class FakeReportService:
    async def get_summary(self, **kwargs):
        from locker_pulse_api.schemas import ReportSummary

        return ReportSummary(
            signal="multiple",
            label="Kilka zgłoszeń dzisiaj",
            message="Ten punkt ma kilka świeżych zgłoszeń problemu.",
            count_24h=2,
            count_window=3,
            window_days=kwargs["days"],
            reasons={"not_working": 2, "full": 1},
        )

    async def create_report(self, **kwargs):
        from locker_pulse_api.schemas import UserReportResponse

        payload = kwargs["payload"]
        return UserReportResponse(
            id="report_1",
            country=kwargs["country"],
            name=kwargs["name"],
            reason=payload.reason,
            comment=payload.comment,
            photos=payload.photos,
            source="web",
            created_at=datetime.now(timezone.utc),
            summary=await self.get_summary(country=kwargs["country"], name=kwargs["name"], days=7),
        )


def override_report_service():
    return FakeReportService()


class FakeReportTriageService:
    async def analyze_report(self, **kwargs):
        return None

    async def get_public_analysis(self, **kwargs):
        return None


def override_report_triage_service():
    return FakeReportTriageService()


class FakeAdminReportService:
    async def list_reports(self, **kwargs):
        from locker_pulse_api.schemas import AdminReportItem, AdminReportListResponse

        item = AdminReportItem(
            id="report_1",
            country="PL",
            name="SYZ01M",
            reason="screen_problem",
            comment="Ekran nie reaguje na dotyk.",
            photos_count=1,
            source="web",
            created_at=datetime.now(timezone.utc),
            point_address="Strzyzewice 108",
            analysis_status="ok",
            analysis=None,
        )
        return AdminReportListResponse(count=1, items=[item])

    async def delete_report(self, **kwargs):
        from locker_pulse_api.schemas import AdminDeleteReportResponse

        return AdminDeleteReportResponse(deleted=True, report_id=kwargs["report_id"])


def override_admin_report_service():
    return FakeAdminReportService()


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_endpoint_uses_validated_query_contract():
    app.dependency_overrides[get_point_service] = override_service
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/points/search",
                params={
                    "lat": 52.2297,
                    "lng": 21.0122,
                    "functions": "parcel_collect,parcel_send",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["radius_m"] == 3000
    assert payload["query"]["functions"] == ["parcel_collect", "parcel_send"]
    assert payload["items"][0]["score"] == 95
    assert payload["alerts"] == []


def test_search_rejects_radius_above_inpost_limit():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/points/search",
            params={"lat": 52.2297, "lng": 21.0122, "radius_m": 50001},
        )

    assert response.status_code == 422


def test_point_detail_accepts_location_context():
    app.dependency_overrides[get_point_service] = override_service
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/points/PL/WAW198M",
                params={"lat": 52.2297, "lng": 21.0122, "radius_m": 3000},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["distance_m"] == 124
    assert payload["score"] == 95


def test_point_alternatives_endpoint_returns_recommendations():
    app.dependency_overrides[get_point_service] = override_service
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/points/PL/WAW198M/alternatives",
                params={"lat": 52.2297, "lng": 21.0122, "radius_m": 3000},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk"]["level"] == "critical"
    assert payload["alternatives"][0]["name"] == "WAW200M"


def test_geocode_endpoint_returns_coordinates():
    app.dependency_overrides[get_geocoding_service] = override_geocoding_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/geocode", params={"q": "Dluga 1, Gdansk"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["coordinates"] == {"lat": 54.351, "lng": 18.646}
    assert payload["display_name"] == "Dluga 1, Gdansk, Polska"


def test_geocode_suggest_endpoint_returns_address_candidates():
    app.dependency_overrides[get_geocoding_service] = override_geocoding_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/geocode/suggest", params={"q": "Dluga", "limit": 2})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["items"][0]["display_name"] == "Dluga 1, Gdansk, Polska"


def test_point_history_endpoint_returns_reliability_timeline():
    app.dependency_overrides[get_reliability_service] = override_reliability_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/points/PL/WAW198M/history", params={"days": 7})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["reliability"]["label"] == "stabilny"
    assert payload["timeline"][0]["status"] == "Operating"
    assert payload["events"][0]["from_status"] == "Disabled"


def test_report_summary_endpoint_returns_community_signal():
    app.dependency_overrides[get_report_service] = override_report_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/points/PL/SYZ01M/reports/summary", params={"days": 7})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"] == "multiple"
    assert payload["count_24h"] == 2


def test_create_report_endpoint_validates_and_saves_report():
    app.dependency_overrides[get_report_service] = override_report_service
    app.dependency_overrides[get_report_triage_service] = override_report_triage_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/points/PL/SYZ01M/reports",
                json={
                    "reason": "screen_problem",
                    "comment": "Ekran nie reaguje na dotyk.",
                    "photos": [
                        {
                            "file_name": "ekran.png",
                            "content_type": "image/png",
                            "size_bytes": 128,
                            "data_url": "data:image/png;base64,aaaaaaaaaaaaaaaaaaaaaaaa",
                        }
                    ],
                    "lat": 51.0808,
                    "lng": 22.4416,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["reason"] == "screen_problem"
    assert payload["photos"][0]["file_name"] == "ekran.png"
    assert payload["summary"]["signal"] == "multiple"


def test_create_report_rejects_short_comment():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/points/PL/SYZ01M/reports",
            json={"reason": "other", "comment": "za krótko"},
        )

    assert response.status_code == 422


def test_admin_reports_endpoint_lists_reports():
    app.dependency_overrides[get_admin_report_service] = override_admin_report_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/reports")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == "report_1"


def test_admin_delete_report_endpoint_deletes_report():
    app.dependency_overrides[get_admin_report_service] = override_admin_report_service
    try:
        with TestClient(app) as client:
            response = client.delete("/api/v1/admin/reports/report_1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"deleted": True, "report_id": "report_1"}
