import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.db import connect_database, disconnect_database
from locker_pulse_api.repositories.point_repository import _point_payload
from locker_pulse_api.services.scoring import score_point

try:
    from prisma import Json as PrismaJson
except Exception:  # pragma: no cover - used before generated client exists
    PrismaJson = lambda value: value  # noqa: E731


logger = logging.getLogger(__name__)
DEMO_NOTE = (
    "Dane przykładowe zasiane lokalnie do prezentacji panelu Niezawodność. "
    "Nie pochodzą z realnego monitoringu InPost."
)


@dataclass(frozen=True)
class DemoPointCase:
    name: str
    address_line1: str
    address_line2: str
    city: str
    province: str
    post_code: str
    street: str
    building_number: str
    lat: float
    lng: float
    statuses: tuple[str, ...]
    availability: tuple[str, ...]
    location_247: bool
    easy_access: bool
    physical_type: str
    functions: tuple[str, ...]
    demo_case: str


DEMO_CASES: tuple[DemoPointCase, ...] = (
    DemoPointCase(
        name="SYZ01M",
        address_line1="Strzyżewice 108",
        address_line2="23-107 Strzyżewice",
        city="Strzyżewice",
        province="lubelskie",
        post_code="23-107",
        street="Strzyżewice",
        building_number="108",
        lat=51.0808,
        lng=22.4416,
        statuses=(
            "Operating",
            "Disabled",
            "Operating",
            "Disabled",
            "Disabled",
            "Operating",
            "Disabled",
            "Disabled",
            "Disabled",
            "Disabled",
        ),
        availability=("NO_DATA",) * 10,
        location_247=False,
        easy_access=False,
        physical_type="classic",
        functions=("parcel_collect",),
        demo_case="problem teraz: dużo awarii i aktualny status Disabled",
    ),
    DemoPointCase(
        name="SYZGOOD1",
        address_line1="Strzyżewice 118A",
        address_line2="23-107 Strzyżewice",
        city="Strzyżewice",
        province="lubelskie",
        post_code="23-107",
        street="Strzyżewice",
        building_number="118A",
        lat=51.084,
        lng=22.447,
        statuses=("Operating",) * 10,
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=True,
        physical_type="newfm",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="alternatywa dla SYZ01M: stabilny i blisko",
    ),
    DemoPointCase(
        name="SYZGOOD2",
        address_line1="Piotrowice 12",
        address_line2="23-107 Strzyżewice",
        city="Strzyżewice",
        province="lubelskie",
        post_code="23-107",
        street="Piotrowice",
        building_number="12",
        lat=51.096,
        lng=22.425,
        statuses=("Operating",) * 10,
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=True,
        physical_type="next",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="alternatywa dla SYZ01M: stabilny punkt w tym samym promieniu",
    ),
    DemoPointCase(
        name="WAWSTABLE1",
        address_line1="Marszałkowska 104/122",
        address_line2="00-017 Warszawa",
        city="Warszawa",
        province="mazowieckie",
        post_code="00-017",
        street="Marszałkowska",
        building_number="104/122",
        lat=52.2319,
        lng=21.0067,
        statuses=("Operating",) * 10,
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=True,
        physical_type="newfm",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="stabilny punkt: 10/10 pomiarów Operating",
    ),
    DemoPointCase(
        name="GDARATHER1",
        address_line1="Długa 1",
        address_line2="80-827 Gdańsk",
        city="Gdańsk",
        province="pomorskie",
        post_code="80-827",
        street="Długa",
        building_number="1",
        lat=54.3504,
        lng=18.6534,
        statuses=(
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Disabled",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
        ),
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=True,
        physical_type="next",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="raczej stabilny: jeden krótki problem w środku tygodnia",
    ),
    DemoPointCase(
        name="LODFLIP1",
        address_line1="Piotrkowska 86",
        address_line2="90-103 Łódź",
        city="Łódź",
        province="łódzkie",
        post_code="90-103",
        street="Piotrkowska",
        building_number="86",
        lat=51.7671,
        lng=19.456,
        statuses=(
            "Operating",
            "Disabled",
            "Operating",
            "Disabled",
            "Operating",
            "Disabled",
            "Operating",
            "Disabled",
            "Operating",
            "Operating",
        ),
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=False,
        physical_type="newfm",
        functions=("parcel_collect", "parcel_send"),
        demo_case="niestabilny: częste przełączanie Operating/Disabled",
    ),
    DemoPointCase(
        name="POZDOWN1",
        address_line1="Półwiejska 42",
        address_line2="61-888 Poznań",
        city="Poznań",
        province="wielkopolskie",
        post_code="61-888",
        street="Półwiejska",
        building_number="42",
        lat=52.4021,
        lng=16.9292,
        statuses=(
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Disabled",
            "Disabled",
            "Disabled",
        ),
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=True,
        physical_type="modular",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="problem teraz: działał długo, ale ostatnie pomiary są Disabled",
    ),
    DemoPointCase(
        name="WROSHORT1",
        address_line1="Rynek 14",
        address_line2="50-101 Wrocław",
        city="Wrocław",
        province="dolnośląskie",
        post_code="50-101",
        street="Rynek",
        building_number="14",
        lat=51.1094,
        lng=17.0326,
        statuses=("Operating",),
        availability=("NO_DATA",),
        location_247=True,
        easy_access=True,
        physical_type="newfm",
        functions=("parcel_collect", "parcel_send"),
        demo_case="za mało danych: tylko jeden przykładowy snapshot",
    ),
    DemoPointCase(
        name="LUBAVAIL1",
        address_line1="Krakowskie Przedmieście 40",
        address_line2="20-002 Lublin",
        city="Lublin",
        province="lubelskie",
        post_code="20-002",
        street="Krakowskie Przedmieście",
        building_number="40",
        lat=51.2465,
        lng=22.5674,
        statuses=("Operating",) * 10,
        availability=(
            "NO_DATA",
            "NO_DATA",
            "AVAILABLE",
            "AVAILABLE",
            "FULL",
            "AVAILABLE",
            "NO_DATA",
            "NO_DATA",
            "NO_DATA",
            "NO_DATA",
        ),
        location_247=True,
        easy_access=True,
        physical_type="next",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="stabilny status, ale zmieniające się pole locker_availability",
    ),
    DemoPointCase(
        name="RZECREATED1",
        address_line1="3 Maja 2",
        address_line2="35-030 Rzeszów",
        city="Rzeszów",
        province="podkarpackie",
        post_code="35-030",
        street="3 Maja",
        building_number="2",
        lat=50.0381,
        lng=22.0047,
        statuses=(
            "Created",
            "Created",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
        ),
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=False,
        physical_type="newfm",
        functions=("parcel_collect", "parcel_send"),
        demo_case="punkt po uruchomieniu: pierwsze pomiary Created, potem Operating",
    ),
    DemoPointCase(
        name="BIALOW1",
        address_line1="Lipowa 12",
        address_line2="15-427 Białystok",
        city="Białystok",
        province="podlaskie",
        post_code="15-427",
        street="Lipowa",
        building_number="12",
        lat=53.1325,
        lng=23.1591,
        statuses=("Operating",) * 10,
        availability=("NO_DATA",) * 10,
        location_247=False,
        easy_access=False,
        physical_type="classic",
        functions=("parcel_collect",),
        demo_case="stabilny, ale mniej wygodny: brak 24/7, easy access i nadania",
    ),
    DemoPointCase(
        name="KATMAINT1",
        address_line1="Stawowa 13",
        address_line2="40-095 Katowice",
        city="Katowice",
        province="śląskie",
        post_code="40-095",
        street="Stawowa",
        building_number="13",
        lat=50.2604,
        lng=19.0216,
        statuses=(
            "Operating",
            "Operating",
            "Disabled",
            "Operating",
            "Operating",
            "Disabled",
            "Operating",
            "Operating",
            "Operating",
            "Operating",
        ),
        availability=("NO_DATA",) * 10,
        location_247=True,
        easy_access=True,
        physical_type="modular",
        functions=("parcel_collect", "parcel_send", "parcel_return"),
        demo_case="niestabilny: dwie przerwy serwisowe w tygodniu",
    ),
)


async def seed_demo_history() -> None:
    settings = get_settings()
    db = await connect_database(settings)
    if db is None:
        raise RuntimeError("Demo history seed requires DATABASE_URL and a generated Prisma client.")

    started = datetime.now(timezone.utc)
    event_count = 0
    snapshot_count = 0
    names = [case.name for case in DEMO_CASES]

    try:
        await db.pointstatusevent.delete_many(where={"country": "PL", "name": {"in": names}})
        await db.pointsnapshot.delete_many(where={"country": "PL", "name": {"in": names}})
        await db.userreport.delete_many(where={"country": "PL", "name": {"in": names}, "isDemo": True})

        collector_run = await db.collectorrun.create(
            data={
                "mode": "demo_history_seed",
                "status": "running",
                "targetCount": len(DEMO_CASES),
            }
        )

        for case in DEMO_CASES:
            latest_raw = _raw_point(
                case,
                status=case.statuses[-1],
                availability_status=_availability_at(case, len(case.statuses) - 1),
            )
            saved_point = await db.point.upsert(
                where={
                    "country_name": {
                        "country": "PL",
                        "name": case.name,
                    }
                },
                data={
                    "create": _point_payload(latest_raw),
                    "update": _point_payload(latest_raw),
                },
            )

            previous_status: str | None = None
            previous_availability: str | None = None
            for index, collected_at in enumerate(_snapshot_times(len(case.statuses))):
                status = case.statuses[index]
                availability = _availability_at(case, index)
                raw = _raw_point(case, status=status, availability_status=availability)
                score = score_point(raw, requested_functions=[], radius_m=3000)
                await db.pointsnapshot.create(
                    data={
                        "pointId": saved_point.id,
                        "collectorRunId": collector_run.id,
                        "country": "PL",
                        "name": case.name,
                        "status": status,
                        "lockerAvailabilityStatus": availability,
                        "score": score.score,
                        "grade": score.grade,
                        "location247": case.location_247,
                        "easyAccessZone": case.easy_access,
                        "physicalType": case.physical_type,
                        "functions": PrismaJson(list(case.functions)),
                        "raw": PrismaJson(raw),
                        "collectedAt": collected_at,
                    }
                )
                snapshot_count += 1

                if previous_status is not None and (
                    previous_status != status or previous_availability != availability
                ):
                    await db.pointstatusevent.create(
                        data={
                            "pointId": saved_point.id,
                            "collectorRunId": collector_run.id,
                            "country": "PL",
                            "name": case.name,
                            "eventType": _event_type(previous_status, status, previous_availability, availability),
                            "fromStatus": previous_status,
                            "toStatus": status,
                            "fromLockerAvailabilityStatus": previous_availability,
                            "toLockerAvailabilityStatus": availability,
                            "detectedAt": collected_at,
                        }
                    )
                    event_count += 1

                previous_status = status
                previous_availability = availability

            for report in _demo_reports(case):
                saved_report = await db.userreport.create(
                    data={
                        "pointId": saved_point.id,
                        "country": "PL",
                        "name": case.name,
                        "reason": report["reason"],
                        "comment": report["comment"],
                        "source": "demo_seed",
                        "isDemo": True,
                        "createdAt": datetime.now(timezone.utc) - timedelta(hours=report["hours_ago"]),
                    }
                )
                demo_analysis = _demo_analysis(case, report)
                if demo_analysis:
                    await db.userreportanalysis.create(
                        data={
                            "reportId": saved_report.id,
                            "severity": demo_analysis["severity"],
                            "confidence": demo_analysis["confidence"],
                            "category": demo_analysis["category"],
                            "isActionable": demo_analysis["is_actionable"],
                            "spamLikelihood": demo_analysis["spam_likelihood"],
                            "photoEvidence": demo_analysis["photo_evidence"],
                            "recommendedRiskFloor": demo_analysis["recommended_risk_floor"],
                            "scorePenalty": demo_analysis["score_penalty"],
                            "summary": demo_analysis["summary"],
                            "evidence": PrismaJson(demo_analysis["evidence"]),
                            "modelName": "demo-rules",
                            "promptVersion": "report-triage-v1",
                            "provider": "rules",
                            "analysisMode": "rules",
                            "usedImages": False,
                            "rawResponse": PrismaJson(demo_analysis),
                            "status": "ok",
                            "startedAt": datetime.now(timezone.utc) - timedelta(hours=report["hours_ago"]),
                            "finishedAt": datetime.now(timezone.utc) - timedelta(hours=report["hours_ago"], minutes=-1),
                        }
                    )

        duration_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        await db.collectorrun.update(
            where={"id": collector_run.id},
            data={
                "status": "ok",
                "pointCount": len(DEMO_CASES),
                "snapshotCount": snapshot_count,
                "eventCount": event_count,
                "durationMs": duration_ms,
                "finishedAt": datetime.now(timezone.utc),
            },
        )
        logger.info(
            "Seeded %s demo points, %s snapshots and %s events.",
            len(DEMO_CASES),
            snapshot_count,
            event_count,
        )
    finally:
        await disconnect_database(db)


def _raw_point(case: DemoPointCase, *, status: str, availability_status: str) -> dict[str, Any]:
    return {
        "country": "PL",
        "name": case.name,
        "type": ["parcel_locker"],
        "status": status,
        "location": {
            "latitude": case.lat,
            "longitude": case.lng,
        },
        "distance": 0,
        "address": {
            "line1": case.address_line1,
            "line2": case.address_line2,
        },
        "address_details": {
            "city": case.city,
            "province": case.province,
            "post_code": case.post_code,
            "street": case.street,
            "building_number": case.building_number,
        },
        "location_description": f"Demo: {case.demo_case}",
        "opening_hours": "24/7" if case.location_247 else "sprawdź lokalnie",
        "functions": list(case.functions),
        "location_247": case.location_247,
        "easy_access_zone": case.easy_access,
        "physical_type": case.physical_type,
        "image_url": None,
        "locker_availability": {
            "status": availability_status,
        },
        "unavailability_periods": [],
        "demo_history": True,
        "demo_case": case.demo_case,
        "demo_note": DEMO_NOTE,
    }


def _snapshot_times(count: int) -> list[datetime]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if count == 1:
        return [now - timedelta(hours=1)]

    span = timedelta(days=6)
    step = span / (count - 1)
    return [now - span + (step * index) for index in range(count)]


def _availability_at(case: DemoPointCase, index: int) -> str:
    if index < len(case.availability):
        return case.availability[index]
    return case.availability[-1]


def _event_type(
    previous_status: str,
    next_status: str,
    previous_availability: str | None,
    next_availability: str | None,
) -> str:
    status_changed = previous_status != next_status
    availability_changed = previous_availability != next_availability
    if status_changed and availability_changed:
        return "status_and_availability_changed"
    if status_changed:
        return "status_changed"
    return "availability_changed"


def _demo_reports(case: DemoPointCase) -> list[dict[str, Any]]:
    if case.name == "SYZ01M":
        return [
            {
                "reason": "not_working",
                "comment": "Demo: skrytka nie otworzyła się po wpisaniu kodu.",
                "hours_ago": 2,
            },
            {
                "reason": "screen_problem",
                "comment": "Demo: ekran nie reagował na dotyk przez kilka prób.",
                "hours_ago": 4,
            },
            {
                "reason": "access_problem",
                "comment": "Demo: trudno było dostać się do urządzenia przy wejściu.",
                "hours_ago": 8,
            },
            {
                "reason": "full",
                "comment": "Demo: nie było wolnej skrytki do nadania paczki.",
                "hours_ago": 11,
            },
        ]
    if case.name == "LODFLIP1":
        return [
            {
                "reason": "not_working",
                "comment": "Demo: punkt raz działał, raz odmawiał przyjęcia paczki.",
                "hours_ago": 3,
            },
            {
                "reason": "screen_problem",
                "comment": "Demo: ekran zawiesił się podczas próby nadania.",
                "hours_ago": 14,
            },
        ]
    return []


def _demo_analysis(case: DemoPointCase, report: dict[str, Any]) -> dict[str, Any] | None:
    if case.name == "SYZ01M":
        severity_by_reason = {
            "not_working": 88,
            "screen_problem": 78,
            "access_problem": 62,
            "full": 58,
        }
        severity = severity_by_reason.get(report["reason"], 55)
        return {
            "severity": severity,
            "confidence": 0.84,
            "category": report["reason"],
            "is_actionable": True,
            "spam_likelihood": 0,
            "photo_evidence": "none",
            "recommended_risk_floor": "critical" if severity >= 86 else "risky",
            "score_penalty": 30 if severity >= 86 else 20 if severity >= 66 else 10,
            "summary": "Demo AI: zgłoszenie wskazuje realny problem z użyciem punktu.",
            "evidence": ["Komentarz opisuje problem funkcjonalny", "Zgłoszenie jest świeże"],
        }
    if case.name == "LODFLIP1":
        return {
            "severity": 72,
            "confidence": 0.78,
            "category": report["reason"],
            "is_actionable": True,
            "spam_likelihood": 0,
            "photo_evidence": "none",
            "recommended_risk_floor": "risky",
            "score_penalty": 20,
            "summary": "Demo AI: zgłoszenie wzmacnia obraz niestabilnego punktu.",
            "evidence": ["Komentarz pasuje do historii zmian statusu"],
        }
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(seed_demo_history())


if __name__ == "__main__":
    main()
