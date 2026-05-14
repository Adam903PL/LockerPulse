from math import atan2, cos, radians, sin, sqrt
from time import perf_counter
from typing import Any

from locker_pulse_api.clients.inpost import InPostApiError, InPostClient
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.schemas import (
    Coordinates,
    PointAlternativesResponse,
    PointSearchResponse,
    PointSummary,
    SearchInsights,
    SearchQueryEcho,
)
from locker_pulse_api.services.advice import (
    alternatives_message,
    build_search_alerts,
    classify_point_risk,
    plan_b_message,
    select_alternatives,
)
from locker_pulse_api.services.reliability import ReliabilityService, reliability_adjustment
from locker_pulse_api.services.reports import ReportService
from locker_pulse_api.services.scoring import NO_DATA_WARNING, grade_for_score, score_point


class PointService:
    def __init__(self, inpost_client: InPostClient, point_repository: PointRepository) -> None:
        self._inpost_client = inpost_client
        self._point_repository = point_repository
        self._reliability_service = ReliabilityService(point_repository)
        self._report_service = ReportService(point_repository)

    async def search(
        self,
        *,
        lat: float,
        lng: float,
        radius_m: int,
        limit: int,
        country: str,
        point_type: str,
        functions: list[str],
        open_24_7: bool | None,
        easy_access: bool | None,
        min_score: int | None,
        demo: bool = False,
    ) -> PointSearchResponse:
        started = perf_counter()
        upstream_count: int | None = None
        try:
            payload = await self._inpost_client.search_points(
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                country=country,
                point_type=point_type,
                per_page=max(limit * 3, limit),
            )
            upstream_count = payload.get("count")
            raw_items = payload.get("items") or []
            await self._point_repository.save_points(
                raw_items,
                record_snapshots=True,
                radius_m=radius_m,
            )
            scored_items = [
                _to_point_summary(item, functions=functions, radius_m=radius_m)
                for item in raw_items
            ]
            if demo:
                demo_records = await self._point_repository.get_points_near(
                    country=country,
                    lat=lat,
                    lng=lng,
                    radius_m=radius_m,
                    include_demo=True,
                )
                demo_summaries = [
                    await self._summary_from_cached_record(
                        record,
                        lat=lat,
                        lng=lng,
                        radius_m=radius_m,
                        include_demo=True,
                    )
                    for record in demo_records
                    if _is_demo_point(record)
                ]
                demo_snapshots = await self._point_repository.get_demo_snapshots_near(
                    country=country,
                    lat=lat,
                    lng=lng,
                    radius_m=radius_m,
                )
                demo_summaries.extend(
                    [
                        await self._summary_from_cached_record(
                            snapshot,
                            lat=lat,
                            lng=lng,
                            radius_m=radius_m,
                            include_demo=True,
                        )
                        for snapshot in demo_snapshots
                    ]
                )
                seen_ids = {item.id for item in scored_items}
                for item in demo_summaries:
                    if item.id not in seen_ids:
                        scored_items.append(item)
                        seen_ids.add(item.id)

            scored_items = await self._apply_reliability(scored_items, include_demo=demo)
            filtered_items = _filter_items(
                scored_items,
                functions=functions,
                open_24_7=open_24_7,
                easy_access=easy_access,
                min_score=min_score,
            )
            ranked_items = sorted(
                filtered_items,
                key=lambda item: (-item.score, item.distance_m if item.distance_m is not None else 10**9),
            )[:limit]
            alerts = build_search_alerts(ranked_items)

            duration_ms = round((perf_counter() - started) * 1000)
            await self._point_repository.log_search(
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                country=country,
                point_type=point_type,
                functions=functions,
                result_count=len(ranked_items),
                upstream_count=upstream_count,
                duration_ms=duration_ms,
                status="ok",
            )

            return PointSearchResponse(
                query=SearchQueryEcho(
                    lat=lat,
                    lng=lng,
                    radius_m=radius_m,
                    country=country,
                    type=point_type,
                    functions=functions,
                    open_24_7=open_24_7,
                    easy_access=easy_access,
                    min_score=min_score,
                    demo=demo,
                ),
                count=len(ranked_items),
                upstream_count=upstream_count,
                items=ranked_items,
                insights=_build_insights(scored_items),
                alerts=alerts,
            )
        except InPostApiError as exc:
            duration_ms = round((perf_counter() - started) * 1000)
            await self._point_repository.log_search(
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                country=country,
                point_type=point_type,
                functions=functions,
                result_count=0,
                upstream_count=upstream_count,
                duration_ms=duration_ms,
                status="error",
                error=str(exc),
            )
            raise

    async def get_point(
        self,
        *,
        country: str,
        name: str,
        lat: float | None = None,
        lng: float | None = None,
        radius_m: int = 50_000,
        demo: bool = False,
    ) -> PointSummary:
        demo_snapshot = await self._point_repository.get_demo_snapshot(country=country, name=name) if demo else None
        if demo_snapshot is not None:
            return await self._summary_from_cached_record(
                demo_snapshot,
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                include_demo=True,
            )

        cached_point = await self._point_repository.get_point_record(country=country, name=name)
        if demo and _is_demo_point(cached_point):
            return await self._summary_from_cached_record(
                cached_point,
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                include_demo=True,
            )

        try:
            point = await self._inpost_client.get_point(country=country, name=name)
        except InPostApiError:
            if cached_point is not None and (demo or not _is_demo_point(cached_point)):
                return await self._summary_from_cached_record(
                    cached_point,
                    lat=lat,
                    lng=lng,
                    radius_m=radius_m,
                    include_demo=demo,
                )
            raise

        if lat is not None and lng is not None:
            point = {**point, "distance": _distance_from_reference(point, lat=lat, lng=lng)}
        await self._point_repository.save_points(
            [point],
            record_snapshots=True,
            radius_m=radius_m,
        )
        summary = _to_point_summary(point, functions=[], radius_m=radius_m)
        return await self._apply_reliability_to_item(summary, include_demo=demo)

    async def get_alternatives(
        self,
        *,
        country: str,
        name: str,
        lat: float,
        lng: float,
        radius_m: int,
        limit: int,
        demo: bool = False,
    ) -> PointAlternativesResponse:
        point = await self.get_point(
            country=country,
            name=name,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            demo=demo,
        )
        candidates = await self._alternative_candidates(
            country=country,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            limit=max(20, limit * 8),
            include_demo=demo,
        )
        alternatives = select_alternatives(point, candidates, limit=limit)
        risk = point.risk or classify_point_risk(point)
        return PointAlternativesResponse(
            point=point,
            risk=risk,
            alternatives=alternatives,
            message=alternatives_message(point, alternatives),
            plan_b_message=plan_b_message(point, alternatives),
        )

    async def _summary_from_cached_record(
        self,
        record: Any,
        *,
        lat: float | None,
        lng: float | None,
        radius_m: int,
        include_demo: bool = False,
    ) -> PointSummary:
        point = _record_to_point(record)
        if lat is not None and lng is not None:
            point = {**point, "distance": _distance_from_reference(point, lat=lat, lng=lng)}
        summary = _to_point_summary(point, functions=[], radius_m=radius_m)
        return await self._apply_reliability_to_item(summary, include_demo=include_demo)

    async def _apply_reliability(self, items: list[PointSummary], *, include_demo: bool = False) -> list[PointSummary]:
        return [await self._apply_reliability_to_item(item, include_demo=include_demo) for item in items]

    async def _apply_reliability_to_item(self, item: PointSummary, *, include_demo: bool = False) -> PointSummary:
        reliability = await self._reliability_service.get_summary(
            country=item.country,
            name=item.name,
            days=7,
            include_demo=include_demo,
        )
        report_summary = await self._report_service.get_summary(
            country=item.country,
            name=item.name,
            days=7,
            include_demo=include_demo,
        )
        adjustment = reliability_adjustment(reliability)
        score_adjustment = adjustment.adjustment
        if item.status != "Operating" and score_adjustment > 0:
            score_adjustment = 0

        adjusted_score = _cap_score_for_status(
            score=max(0, min(100, item.score + score_adjustment)),
            status=item.status,
        )
        community_penalty = report_summary.community_penalty
        final_score = _cap_score_for_status(
            score=max(0, min(100, adjusted_score - community_penalty)),
            status=item.status,
        )
        problem_reasons = _problem_reasons(report_summary)

        updated = item.model_copy(
            update={
                "score": final_score,
                "grade": grade_for_score(final_score),
                "reliability": reliability,
                "report_summary": report_summary,
                "base_score": adjusted_score,
                "community_penalty": community_penalty,
                "problem_score_24h": report_summary.problem_score_24h,
                "problem_reasons": problem_reasons,
                "history_adjustment": score_adjustment,
                "history_reasons": adjustment.reasons,
                "history_warnings": adjustment.warnings,
            }
        )
        return updated.model_copy(update={"risk": classify_point_risk(updated)})

    async def _alternative_candidates(
        self,
        *,
        country: str,
        lat: float,
        lng: float,
        radius_m: int,
        limit: int,
        include_demo: bool = False,
    ) -> list[PointSummary]:
        raw_items: list[dict[str, Any]] = []
        try:
            payload = await self._inpost_client.search_points(
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                country=country,
                point_type="parcel_locker_only",
                per_page=min(max(limit, 1), 100),
            )
            raw_items = payload.get("items") or []
            await self._point_repository.save_points(
                raw_items,
                record_snapshots=True,
                radius_m=radius_m,
            )
        except InPostApiError:
            raw_items = []

        candidate_map: dict[str, PointSummary] = {}
        live_summaries = [
            _to_point_summary(_with_distance(item, lat=lat, lng=lng), functions=[], radius_m=radius_m)
            for item in raw_items
        ]
        for item in await self._apply_reliability(live_summaries, include_demo=include_demo):
            candidate_map[item.id] = item

        cached_records = await self._point_repository.get_points_near(
            country=country,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            include_demo=include_demo,
        )
        cached_summaries = [
            await self._summary_from_cached_record(
                record,
                lat=lat,
                lng=lng,
                radius_m=radius_m,
                include_demo=include_demo,
            )
            for record in cached_records
            if include_demo or not _is_demo_point(record)
        ]
        for item in cached_summaries:
            if item.distance_m is not None and item.distance_m <= radius_m:
                candidate_map[item.id] = item

        return list(candidate_map.values())


def _to_point_summary(
    point: dict[str, Any],
    *,
    functions: list[str],
    radius_m: int,
) -> PointSummary:
    score = score_point(point, requested_functions=functions, radius_m=radius_m)
    address = point.get("address") or {}
    details = point.get("address_details") or {}
    location = point.get("location") or {}
    latitude = float(location.get("latitude") or 0)
    longitude = float(location.get("longitude") or 0)

    return PointSummary(
        id=f"{point.get('country')}:{point.get('name')}",
        name=point.get("name") or "",
        country=point.get("country") or "",
        status=point.get("status"),
        distance_m=point.get("distance"),
        address=_format_address(address, details),
        city=details.get("city"),
        province=details.get("province"),
        post_code=details.get("post_code"),
        coordinates=Coordinates(lat=latitude, lng=longitude),
        score=score.score,
        grade=score.grade,
        reasons=score.reasons,
        warnings=score.warnings,
        location_247=point.get("location_247") is True,
        easy_access_zone=point.get("easy_access_zone") is True,
        physical_type=point.get("physical_type"),
        image_url=point.get("image_url"),
        functions=point.get("functions") or [],
    )


def _filter_items(
    items: list[PointSummary],
    *,
    functions: list[str],
    open_24_7: bool | None,
    easy_access: bool | None,
    min_score: int | None,
) -> list[PointSummary]:
    filtered = items
    if functions:
        required = set(functions)
        filtered = [item for item in filtered if required.issubset(set(item.functions))]
    if open_24_7 is not None:
        filtered = [item for item in filtered if item.location_247 is open_24_7]
    if easy_access is not None:
        filtered = [item for item in filtered if item.easy_access_zone is easy_access]
    if min_score is not None:
        filtered = [item for item in filtered if item.score >= min_score]
    return filtered


def _build_insights(items: list[PointSummary]) -> SearchInsights:
    return SearchInsights(
        operating=sum(1 for item in items if item.status == "Operating"),
        availability_no_data=sum(
            1
            for item in items
            if NO_DATA_WARNING in item.warnings
        ),
        open_24_7=sum(1 for item in items if item.location_247),
        easy_access=sum(1 for item in items if item.easy_access_zone),
    )


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


def _distance_from_reference(point: dict[str, Any], *, lat: float, lng: float) -> int | None:
    location = point.get("location") or {}
    point_lat = location.get("latitude")
    point_lng = location.get("longitude")
    if point_lat is None or point_lng is None:
        return None

    return round(_haversine_m(lat, lng, float(point_lat), float(point_lng)))


def _with_distance(point: dict[str, Any], *, lat: float, lng: float) -> dict[str, Any]:
    if point.get("distance") is not None:
        return point
    return {**point, "distance": _distance_from_reference(point, lat=lat, lng=lng)}


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


def _cap_score_for_status(*, score: int, status: str | None) -> int:
    if status == "Operating":
        return score
    if status == "Disabled":
        return min(score, 25)
    return min(score, 45)


def _problem_reasons(report_summary: Any) -> list[str]:
    reasons: list[str] = []
    if report_summary.community_penalty > 0:
        reasons.append(
            f"Sygnał zgłoszeń: -{report_summary.community_penalty} pkt za świeże zgłoszenia"
        )
    if report_summary.problem_score_24h > 0:
        reasons.append(f"Problem score z ostatnich 24h: {report_summary.problem_score_24h}/100")
    if report_summary.analysis_pending_count > 0:
        reasons.append(f"{report_summary.analysis_pending_count} zgłoszenie/a czeka/ją na analizę AI")
    return reasons


def _is_demo_point(record: Any | None) -> bool:
    raw = _raw_from_record(record)
    return bool(raw and raw.get("demo_history") is True)


def _record_to_point(record: Any) -> dict[str, Any]:
    raw = _raw_from_record(record)
    if raw:
        return dict(raw)

    return {
        "country": getattr(record, "country", ""),
        "name": getattr(record, "name", ""),
        "status": getattr(record, "status", None),
        "type": getattr(record, "pointType", []),
        "location": {
            "latitude": getattr(record, "latitude", 0),
            "longitude": getattr(record, "longitude", 0),
        },
        "distance": getattr(record, "distanceMeters", None),
        "address": {
            "line1": getattr(record, "address", None),
            "line2": None,
        },
        "address_details": {
            "city": getattr(record, "city", None),
            "province": getattr(record, "province", None),
            "post_code": getattr(record, "postCode", None),
            "street": getattr(record, "street", None),
            "building_number": getattr(record, "buildingNumber", None),
        },
        "location_247": getattr(record, "location247", False),
        "easy_access_zone": getattr(record, "easyAccessZone", False),
        "physical_type": getattr(record, "physicalType", None),
        "image_url": getattr(record, "imageUrl", None),
        "locker_availability": {
            "status": getattr(record, "lockerAvailabilityStatus", None),
        },
        "functions": getattr(record, "functions", []),
    }


def _raw_from_record(record: Any | None) -> dict[str, Any] | None:
    if record is None:
        return None
    raw = getattr(record, "raw", None)
    return raw if isinstance(raw, dict) else None
