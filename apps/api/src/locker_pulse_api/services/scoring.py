from dataclasses import dataclass
from typing import Any


NEWER_PHYSICAL_TYPES = {"next", "newfm", "modular"}
CORE_FUNCTIONS = {"parcel_collect", "parcel_send"}
NO_DATA_WARNING = "Źródłowe API zwraca locker_availability=NO_DATA"


@dataclass(frozen=True)
class ScoreResult:
    score: int
    grade: str
    reasons: list[str]
    warnings: list[str]


def score_point(
    point: dict[str, Any],
    *,
    requested_functions: list[str],
    radius_m: int,
) -> ScoreResult:
    score = 0
    reasons: list[str] = []
    warnings: list[str] = []

    status = point.get("status")
    if status == "Operating":
        score += 35
        reasons.append("Punkt działa poprawnie")
    else:
        warnings.append(f"Status punktu: {status or 'unknown'}")

    distance = _safe_int(point.get("distance"))
    if distance is not None:
        distance_score = max(0, round(20 * (1 - min(distance, radius_m) / radius_m)))
        score += distance_score
        reasons.append(f"{_format_distance(distance)} od podanego adresu")
    else:
        warnings.append("Brak danych o odległości")

    if point.get("location_247") is True:
        score += 15
        reasons.append("Dostępny 24/7")
    else:
        warnings.append("Nieoznaczony jako 24/7")

    if point.get("easy_access_zone") is True:
        score += 10
        reasons.append("Strefa łatwego dostępu")
    else:
        warnings.append("Brak oznaczenia strefy łatwego dostępu")

    functions = set(point.get("functions") or [])
    if requested_functions:
        missing = sorted(set(requested_functions) - functions)
        if not missing:
            score += 10
            reasons.append("Obsługuje wymagane akcje")
        else:
            warnings.append(f"Brak wymaganych akcji: {', '.join(missing)}")
    elif CORE_FUNCTIONS.issubset(functions):
        score += 10
        reasons.append("Obsługuje odbiór i nadanie")
    else:
        warnings.append("Podstawowe akcje paczkowe są niepełne")

    physical_type = point.get("physical_type")
    if physical_type in NEWER_PHYSICAL_TYPES:
        score += 5
        reasons.append(f"Nowszy typ urządzenia: {physical_type}")

    if _has_complete_public_details(point):
        score += 5
        reasons.append("Ma zdjęcie i czytelny adres")
    else:
        warnings.append("Zdjęcie albo opis lokalizacji są niepełne")

    availability_status = (point.get("locker_availability") or {}).get("status")
    if availability_status == "NO_DATA":
        warnings.append(NO_DATA_WARNING)

    final_score = _apply_status_cap(max(0, min(100, score)), status, warnings)
    return ScoreResult(
        score=final_score,
        grade=grade_for_score(final_score),
        reasons=reasons,
        warnings=warnings,
    )


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_distance(distance_m: int) -> str:
    if distance_m < 1000:
        return f"{distance_m} m"
    return f"{distance_m / 1000:.1f} km"


def _has_complete_public_details(point: dict[str, Any]) -> bool:
    address = point.get("address") or {}
    return bool(
        point.get("image_url")
        and (point.get("location_description") or address.get("line1") or address.get("line2"))
    )


def _apply_status_cap(score: int, status: str | None, warnings: list[str]) -> int:
    if status == "Operating":
        return score

    cap = 25 if status == "Disabled" else 45
    if score > cap:
        warnings.append(f"Ocena ograniczona do {cap}/100 przez status punktu")
    return min(score, cap)


def grade_for_score(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "fair"
    if score >= 40:
        return "weak"
    return "critical"
