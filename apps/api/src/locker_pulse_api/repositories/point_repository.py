from datetime import datetime, timezone
from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt
from typing import Any

from locker_pulse_api.services.scoring import score_point

try:
    from prisma import Json as PrismaJson
except Exception:  # pragma: no cover - used before generated client exists
    PrismaJson = lambda value: value  # noqa: E731


@dataclass(frozen=True)
class SavePointsResult:
    point_count: int
    snapshot_count: int
    event_count: int


class PointRepository:
    def __init__(self, db: Any | None) -> None:
        self._db = db

    @property
    def enabled(self) -> bool:
        return self._db is not None

    async def save_points(
        self,
        points: list[dict[str, Any]],
        *,
        collector_run_id: str | None = None,
        record_snapshots: bool = False,
        radius_m: int = 50_000,
    ) -> SavePointsResult:
        if not self._db:
            return SavePointsResult(point_count=0, snapshot_count=0, event_count=0)

        point_count = 0
        snapshot_count = 0
        event_count = 0
        for point in points:
            payload = _point_payload(point)
            previous_snapshot = None
            if record_snapshots:
                previous_snapshot = await self.get_latest_snapshot(
                    country=payload["country"],
                    name=payload["name"],
                )

            saved_point = await self._db.point.upsert(
                where={
                    "country_name": {
                        "country": payload["country"],
                        "name": payload["name"],
                    }
                },
                data={
                    "create": payload,
                    "update": payload,
                },
            )
            point_count += 1

            if record_snapshots:
                await self._create_snapshot(
                    point=point,
                    point_id=saved_point.id,
                    collector_run_id=collector_run_id,
                    radius_m=radius_m,
                )
                snapshot_count += 1
                if previous_snapshot is not None:
                    event_created = await self._create_status_event_if_changed(
                        point=point,
                        point_id=saved_point.id,
                        previous_snapshot=previous_snapshot,
                        collector_run_id=collector_run_id,
                    )
                    if event_created:
                        event_count += 1

        return SavePointsResult(
            point_count=point_count,
            snapshot_count=snapshot_count,
            event_count=event_count,
        )

    async def log_search(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: int,
        country: str,
        point_type: str,
        functions: list[str],
        result_count: int,
        upstream_count: int | None,
        duration_ms: int,
        status: str,
        error: str | None = None,
    ) -> None:
        if not self._db:
            return

        await self._db.searchrun.create(
            data={
                "lat": lat,
                "lng": lng,
                "radiusM": radius_m,
                "country": country,
                "pointType": point_type,
                "functions": PrismaJson(functions),
                "resultCount": result_count,
                "upstreamCount": upstream_count,
                "durationMs": duration_ms,
                "status": status,
                "error": error,
            }
        )

    async def start_collector_run(self, *, mode: str, target_count: int) -> str | None:
        if not self._db:
            return None

        run = await self._db.collectorrun.create(
            data={
                "mode": mode,
                "status": "running",
                "targetCount": target_count,
            }
        )
        return run.id

    async def finish_collector_run(
        self,
        *,
        collector_run_id: str | None,
        status: str,
        point_count: int,
        snapshot_count: int,
        event_count: int,
        duration_ms: int,
        error: str | None = None,
    ) -> None:
        if not self._db or collector_run_id is None:
            return

        await self._db.collectorrun.update(
            where={"id": collector_run_id},
            data={
                "status": status,
                "pointCount": point_count,
                "snapshotCount": snapshot_count,
                "eventCount": event_count,
                "durationMs": duration_ms,
                "error": error,
                "finishedAt": datetime.now(timezone.utc),
            },
        )

    async def get_latest_snapshot(self, *, country: str, name: str, include_demo: bool = False) -> Any | None:
        if not self._db:
            return None

        snapshots = await self._db.pointsnapshot.find_many(
            where={"country": country, "name": name},
            order={"collectedAt": "desc"},
            take=20,
        )
        for snapshot in snapshots:
            if include_demo or not _record_has_demo_raw(snapshot):
                return snapshot
        return None

    async def get_demo_snapshot(self, *, country: str, name: str) -> Any | None:
        if not self._db:
            return None

        snapshots = await self._db.pointsnapshot.find_many(
            where={"country": country, "name": name},
            order={"collectedAt": "desc"},
            take=50,
        )
        for snapshot in snapshots:
            raw = getattr(snapshot, "raw", None)
            if isinstance(raw, dict) and raw.get("demo_history") is True:
                return snapshot
        return None

    async def get_demo_snapshots_near(
        self,
        *,
        country: str,
        lat: float,
        lng: float,
        radius_m: int,
        limit: int = 250,
    ) -> list[Any]:
        if not self._db:
            return []

        snapshots = await self._db.pointsnapshot.find_many(
            where={"country": country},
            order={"collectedAt": "desc"},
            take=max(limit * 4, 500),
        )
        selected: list[Any] = []
        seen: set[str] = set()
        for snapshot in snapshots:
            raw = getattr(snapshot, "raw", None)
            if not isinstance(raw, dict) or raw.get("demo_history") is not True:
                continue
            name = getattr(snapshot, "name", None)
            if not name or name in seen:
                continue
            location = raw.get("location") or {}
            point_lat = location.get("latitude")
            point_lng = location.get("longitude")
            if point_lat is None or point_lng is None:
                continue
            distance = _haversine_m(lat, lng, float(point_lat), float(point_lng))
            if distance <= radius_m:
                selected.append(snapshot)
                seen.add(name)
            if len(selected) >= limit:
                break
        return selected

    async def get_point_record(self, *, country: str, name: str) -> Any | None:
        if not self._db:
            return None

        return await self._db.point.find_unique(
            where={
                "country_name": {
                    "country": country,
                    "name": name,
                }
            }
        )

    async def get_points_near(
        self,
        *,
        country: str,
        lat: float,
        lng: float,
        radius_m: int,
        limit: int = 250,
        include_demo: bool = False,
    ) -> list[Any]:
        if not self._db:
            return []

        lat_delta = radius_m / 111_000
        lng_scale = max(0.2, abs(cos(radians(lat))))
        lng_delta = radius_m / (111_000 * lng_scale)

        records = await self._db.point.find_many(
            where={
                "country": country,
                "latitude": {"gte": lat - lat_delta, "lte": lat + lat_delta},
                "longitude": {"gte": lng - lng_delta, "lte": lng + lng_delta},
            },
            take=limit,
        )
        if include_demo:
            return records
        return [record for record in records if not _record_has_demo_raw(record)]

    async def get_snapshots_since(
        self,
        *,
        country: str,
        name: str,
        since: datetime,
        limit: int = 200,
        include_demo: bool = False,
    ) -> list[Any]:
        if not self._db:
            return []

        snapshots = await self._db.pointsnapshot.find_many(
            where={
                "country": country,
                "name": name,
                "collectedAt": {"gte": since},
            },
            order={"collectedAt": "desc"},
            take=limit,
        )
        if include_demo:
            return snapshots
        return [snapshot for snapshot in snapshots if not _record_has_demo_raw(snapshot)]

    async def get_status_events_since(
        self,
        *,
        country: str,
        name: str,
        since: datetime,
        limit: int = 100,
        include_demo: bool = False,
    ) -> list[Any]:
        if not self._db:
            return []

        events = await self._db.pointstatusevent.find_many(
            where={
                "country": country,
                "name": name,
                "detectedAt": {"gte": since},
            },
            include={"collectorRun": True},
            order={"detectedAt": "desc"},
            take=limit,
        )
        if include_demo:
            return events
        return [event for event in events if not _event_is_demo(event)]

    async def create_user_report(
        self,
        *,
        country: str,
        name: str,
        reason: str,
        comment: str,
        photos: list[dict[str, Any]] | None = None,
        lat: float | None = None,
        lng: float | None = None,
        source: str = "web",
        is_demo: bool = False,
    ) -> Any | None:
        if not self._db:
            return None

        point = await self.get_point_record(country=country, name=name)
        if point is None:
            if lat is None or lng is None:
                return None
            point = await self._db.point.upsert(
                where={
                    "country_name": {
                        "country": country,
                        "name": name,
                    }
                },
                data={
                    "create": _report_placeholder_point_payload(
                        country=country,
                        name=name,
                        lat=lat,
                        lng=lng,
                    ),
                    "update": {},
                },
            )

        return await self._db.userreport.create(
            data={
                "pointId": point.id,
                "country": country,
                "name": name,
                "reason": reason,
                "comment": comment,
                "photos": PrismaJson(photos or []),
                "source": source,
                "isDemo": is_demo,
                "lat": lat,
                "lng": lng,
            }
        )

    async def get_user_reports_since(
        self,
        *,
        country: str,
        name: str,
        since: datetime,
        limit: int = 200,
        include_demo: bool = False,
    ) -> list[Any]:
        if not self._db:
            return []

        where: dict[str, Any] = {
            "country": country,
            "name": name,
            "createdAt": {"gte": since},
        }
        if not include_demo:
            where["isDemo"] = False

        return await self._db.userreport.find_many(
            where=where,
            include={"analysis": True},
            order={"createdAt": "desc"},
            take=limit,
        )

    async def get_user_report(self, *, report_id: str) -> Any | None:
        if not self._db:
            return None

        return await self._db.userreport.find_unique(
            where={"id": report_id},
            include={"point": True, "analysis": True},
        )

    async def list_user_reports(self, *, limit: int = 100, include_demo: bool = True) -> list[Any]:
        if not self._db:
            return []

        where: dict[str, Any] = {}
        if not include_demo:
            where["isDemo"] = False

        return await self._db.userreport.find_many(
            where=where,
            include={"point": True, "analysis": True},
            order={"createdAt": "desc"},
            take=limit,
        )

    async def delete_user_report(self, *, report_id: str) -> bool:
        if not self._db:
            return False

        existing = await self._db.userreport.find_unique(where={"id": report_id})
        if existing is None:
            return False
        await self._db.userreport.delete(where={"id": report_id})
        return True

    async def create_report_analysis_pending(
        self,
        *,
        report_id: str,
        model_name: str,
        prompt_version: str,
        provider: str = "rules",
        analysis_mode: str = "rules",
        used_images: bool = False,
    ) -> Any | None:
        if not self._db:
            return None

        return await self._db.userreportanalysis.upsert(
            where={"reportId": report_id},
            data={
                "create": {
                    "reportId": report_id,
                    "severity": 0,
                    "confidence": 0,
                    "category": "unclear",
                    "isActionable": False,
                    "spamLikelihood": 0,
                    "photoEvidence": "none",
                    "recommendedRiskFloor": "none",
                    "scorePenalty": 0,
                    "summary": "",
                    "evidence": PrismaJson([]),
                    "modelName": model_name,
                    "promptVersion": prompt_version,
                    "provider": provider,
                    "analysisMode": analysis_mode,
                    "usedImages": used_images,
                    "status": "pending",
                    "startedAt": datetime.now(timezone.utc),
                },
                "update": {
                    "status": "pending",
                    "error": None,
                    "modelName": model_name,
                    "promptVersion": prompt_version,
                    "provider": provider,
                    "analysisMode": analysis_mode,
                    "usedImages": used_images,
                    "startedAt": datetime.now(timezone.utc),
                    "finishedAt": None,
                },
            },
        )

    async def save_report_analysis_success(
        self,
        *,
        report_id: str,
        severity: int,
        confidence: float,
        category: str,
        is_actionable: bool,
        spam_likelihood: float,
        photo_evidence: str,
        recommended_risk_floor: str,
        score_penalty: int,
        summary: str,
        evidence: list[str],
        model_name: str,
        prompt_version: str,
        provider: str = "rules",
        analysis_mode: str = "rules",
        used_images: bool = False,
        raw_response: dict[str, Any],
        error: str | None = None,
    ) -> Any | None:
        if not self._db:
            return None

        return await self._db.userreportanalysis.upsert(
            where={"reportId": report_id},
            data={
                "create": {
                    "reportId": report_id,
                    "severity": severity,
                    "confidence": confidence,
                    "category": category,
                    "isActionable": is_actionable,
                    "spamLikelihood": spam_likelihood,
                    "photoEvidence": photo_evidence,
                    "recommendedRiskFloor": recommended_risk_floor,
                    "scorePenalty": score_penalty,
                    "summary": summary,
                    "evidence": PrismaJson(evidence),
                    "modelName": model_name,
                    "promptVersion": prompt_version,
                    "provider": provider,
                    "analysisMode": analysis_mode,
                    "usedImages": used_images,
                    "rawResponse": PrismaJson(raw_response),
                    "status": "ok",
                    "error": error[:500] if error else None,
                    "startedAt": datetime.now(timezone.utc),
                    "finishedAt": datetime.now(timezone.utc),
                },
                "update": {
                    "severity": severity,
                    "confidence": confidence,
                    "category": category,
                    "isActionable": is_actionable,
                    "spamLikelihood": spam_likelihood,
                    "photoEvidence": photo_evidence,
                    "recommendedRiskFloor": recommended_risk_floor,
                    "scorePenalty": score_penalty,
                    "summary": summary,
                    "evidence": PrismaJson(evidence),
                    "modelName": model_name,
                    "promptVersion": prompt_version,
                    "provider": provider,
                    "analysisMode": analysis_mode,
                    "usedImages": used_images,
                    "rawResponse": PrismaJson(raw_response),
                    "status": "ok",
                    "error": error[:500] if error else None,
                    "finishedAt": datetime.now(timezone.utc),
                },
            },
        )

    async def save_report_analysis_failure(
        self,
        *,
        report_id: str,
        model_name: str,
        prompt_version: str,
        provider: str = "rules",
        analysis_mode: str = "rules",
        used_images: bool = False,
        error: str,
    ) -> Any | None:
        if not self._db:
            return None

        return await self._db.userreportanalysis.upsert(
            where={"reportId": report_id},
            data={
                "create": {
                    "reportId": report_id,
                    "severity": 0,
                    "confidence": 0,
                    "category": "unclear",
                    "isActionable": False,
                    "spamLikelihood": 0,
                    "photoEvidence": "none",
                    "recommendedRiskFloor": "none",
                    "scorePenalty": 0,
                    "summary": "",
                    "evidence": PrismaJson([]),
                    "modelName": model_name,
                    "promptVersion": prompt_version,
                    "provider": provider,
                    "analysisMode": analysis_mode,
                    "usedImages": used_images,
                    "status": "failed",
                    "error": error[:500],
                    "finishedAt": datetime.now(timezone.utc),
                },
                "update": {
                    "status": "failed",
                    "error": error[:500],
                    "modelName": model_name,
                    "promptVersion": prompt_version,
                    "provider": provider,
                    "analysisMode": analysis_mode,
                    "usedImages": used_images,
                    "finishedAt": datetime.now(timezone.utc),
                },
            },
        )

    async def get_report_analysis(self, *, report_id: str) -> Any | None:
        if not self._db:
            return None

        return await self._db.userreportanalysis.find_unique(
            where={"reportId": report_id},
        )

    async def get_pending_report_ids(self, *, limit: int = 50, include_failed: bool = True) -> list[str]:
        if not self._db:
            return []

        statuses = ["pending", "failed"] if include_failed else ["pending"]
        analyses = await self._db.userreportanalysis.find_many(
            where={"status": {"in": statuses}},
            order={"createdAt": "asc"},
            take=limit,
        )
        return [getattr(analysis, "reportId", "") for analysis in analyses if getattr(analysis, "reportId", "")]

    async def _create_snapshot(
        self,
        *,
        point: dict[str, Any],
        point_id: str,
        collector_run_id: str | None,
        radius_m: int,
    ) -> None:
        score = score_point(point, requested_functions=[], radius_m=radius_m)
        locker_availability = point.get("locker_availability") or {}

        await self._db.pointsnapshot.create(
            data={
                "pointId": point_id,
                "collectorRunId": collector_run_id,
                "country": point.get("country") or "",
                "name": point.get("name") or "",
                "status": point.get("status"),
                "lockerAvailabilityStatus": locker_availability.get("status"),
                "score": score.score,
                "grade": score.grade,
                "location247": point.get("location_247") is True,
                "easyAccessZone": point.get("easy_access_zone") is True,
                "physicalType": point.get("physical_type"),
                "functions": PrismaJson(point.get("functions") or []),
                "raw": PrismaJson(point),
            }
        )

    async def _create_status_event_if_changed(
        self,
        *,
        point: dict[str, Any],
        point_id: str,
        previous_snapshot: Any,
        collector_run_id: str | None,
    ) -> bool:
        previous_status = getattr(previous_snapshot, "status", None)
        next_status = point.get("status")
        previous_availability = getattr(previous_snapshot, "lockerAvailabilityStatus", None)
        next_availability = (point.get("locker_availability") or {}).get("status")

        status_changed = previous_status != next_status
        availability_changed = previous_availability != next_availability
        if not status_changed and not availability_changed:
            return False

        if status_changed and availability_changed:
            event_type = "status_and_availability_changed"
        elif status_changed:
            event_type = "status_changed"
        else:
            event_type = "availability_changed"

        await self._db.pointstatusevent.create(
            data={
                "pointId": point_id,
                "collectorRunId": collector_run_id,
                "country": point.get("country") or "",
                "name": point.get("name") or "",
                "eventType": event_type,
                "fromStatus": previous_status,
                "toStatus": next_status,
                "fromLockerAvailabilityStatus": previous_availability,
                "toLockerAvailabilityStatus": next_availability,
            }
        )
        return True


def _point_payload(point: dict[str, Any]) -> dict[str, Any]:
    address = point.get("address") or {}
    address_details = point.get("address_details") or {}
    location = point.get("location") or {}
    locker_availability = point.get("locker_availability") or {}

    return {
        "country": point.get("country") or "",
        "name": point.get("name") or "",
        "status": point.get("status"),
        "pointType": PrismaJson(point.get("type") or []),
        "latitude": float(location.get("latitude") or 0),
        "longitude": float(location.get("longitude") or 0),
        "distanceMeters": point.get("distance"),
        "address": _format_address(address, address_details),
        "city": address_details.get("city"),
        "province": address_details.get("province"),
        "postCode": address_details.get("post_code"),
        "street": address_details.get("street"),
        "buildingNumber": address_details.get("building_number"),
        "location247": point.get("location_247") is True,
        "easyAccessZone": point.get("easy_access_zone") is True,
        "physicalType": point.get("physical_type"),
        "imageUrl": point.get("image_url"),
        "lockerAvailabilityStatus": locker_availability.get("status"),
        "functions": PrismaJson(point.get("functions") or []),
        "raw": PrismaJson(point),
        "fetchedAt": datetime.now(timezone.utc),
    }


def _format_address(address: dict[str, Any], details: dict[str, Any]) -> str | None:
    if address.get("line1") and address.get("line2"):
        return f"{address['line1']}, {address['line2']}"
    city = details.get("city")
    post_code = details.get("post_code")
    street = details.get("street")
    building = details.get("building_number")
    if city and post_code:
        street_part = f"{street or ''} {building or ''}".strip()
        return f"{street_part}, {post_code} {city}".strip(", ")
    return None


def _record_has_demo_raw(record: Any | None) -> bool:
    raw = getattr(record, "raw", None)
    return isinstance(raw, dict) and raw.get("demo_history") is True


def _event_is_demo(event: Any) -> bool:
    collector_run = getattr(event, "collectorRun", None)
    return getattr(collector_run, "mode", None) == "demo_history_seed"


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_m = 6_371_000
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_m * c


def _report_placeholder_point_payload(*, country: str, name: str, lat: float, lng: float) -> dict[str, Any]:
    raw = {
        "country": country,
        "name": name,
        "location": {
            "latitude": lat,
            "longitude": lng,
        },
        "source": "user_report_placeholder",
    }
    return {
        "country": country,
        "name": name,
        "status": None,
        "pointType": PrismaJson([]),
        "latitude": lat,
        "longitude": lng,
        "distanceMeters": None,
        "address": None,
        "city": None,
        "province": None,
        "postCode": None,
        "street": None,
        "buildingNumber": None,
        "location247": False,
        "easyAccessZone": False,
        "physicalType": None,
        "imageUrl": None,
        "lockerAvailabilityStatus": None,
        "functions": PrismaJson([]),
        "raw": PrismaJson(raw),
    }
