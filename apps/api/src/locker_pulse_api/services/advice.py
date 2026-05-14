from locker_pulse_api.schemas import PointRisk, PointSummary, ReportSummary, SearchAlert

RISK_ORDER = {
    "ok": 0,
    "watch": 1,
    "risky": 2,
    "critical": 3,
}


def classify_point_risk(point: PointSummary) -> PointRisk:
    reasons: list[str] = []
    reliability_label = point.reliability.label if point.reliability else None

    if point.status in {"Disabled", "Created"}:
        reasons.append("Punkt nie ma aktualnie statusu działającego")
    if reliability_label == "problem":
        reasons.append("Ostatni zapis historii wskazuje problem")
    if point.score < 40:
        reasons.append("Ocena punktu jest krytycznie niska")
    if reasons:
        return _with_report_floor(
            PointRisk(
                level="critical",
                label="Krytyczny",
                message="Ten punkt może być dziś problematyczny. Sprawdź alternatywę przed wyjściem.",
                reasons=reasons,
            ),
            point.report_summary,
        )

    if reliability_label == "niestabilny":
        reasons.append("Historia pokazuje częste zmiany statusu")
    if point.score < 60:
        reasons.append("Ocena punktu jest niska")
    if reasons:
        return _with_report_floor(
            PointRisk(
                level="risky",
                label="Ryzyko",
                message="Ten punkt działa, ale wygląda mniej pewnie niż inne w okolicy.",
                reasons=reasons,
            ),
            point.report_summary,
        )

    if reliability_label == "brak historii":
        reasons.append("Nie mamy jeszcze wystarczającej historii")
    if point.score < 75:
        reasons.append("Ocena punktu jest średnia")
    if point.warnings:
        reasons.append("Dane źródłowe mają drobne braki")
    if reasons:
        return _with_report_floor(
            PointRisk(
                level="watch",
                label="Uwaga",
                message="Punkt wygląda używalnie, ale warto sprawdzić szczegóły.",
                reasons=reasons,
            ),
            point.report_summary,
        )

    return _with_report_floor(
        PointRisk(
            level="ok",
            label="Stabilny",
            message="Wygląda na dobry wybór.",
            reasons=["Status, score i historia wyglądają dobrze"],
        ),
        point.report_summary,
    )


def with_risk(point: PointSummary) -> PointSummary:
    return point.model_copy(update={"risk": classify_point_risk(point)})


def build_search_alerts(items: list[PointSummary]) -> list[SearchAlert]:
    affected = [
        item
        for item in items
        if item.risk is not None and item.risk.level in {"risky", "critical"}
    ]
    if not affected:
        return []

    recommended = _recommended_point(items)
    if recommended is not None:
        message = (
            f"W tej okolicy {len(affected)} punkt(y) wygląda ryzykownie. "
            f"Najlepszy wybór teraz: {recommended.name}."
        )
        recommended_id = recommended.id
    else:
        message = (
            f"W tej okolicy {len(affected)} punkt(y) wygląda ryzykownie. "
            "Sprawdź szczegóły przed wyborem."
        )
        recommended_id = None

    severity = "critical" if any(item.risk and item.risk.level == "critical" for item in affected) else "warning"
    return [
        SearchAlert(
            severity=severity,
            title="Warto sprawdzić alternatywę",
            message=message,
            affected_count=len(affected),
            recommended_point_id=recommended_id,
        )
    ]


def select_alternatives(
    point: PointSummary,
    candidates: list[PointSummary],
    *,
    limit: int,
) -> list[PointSummary]:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.id != point.id
        and candidate.status == "Operating"
        and candidate.risk is not None
        and candidate.risk.level != "critical"
    ]
    return sorted(
        eligible,
        key=lambda item: (
            RISK_ORDER.get(item.risk.level if item.risk else "critical", 99),
            -item.score,
            item.distance_m if item.distance_m is not None else 10**9,
        ),
    )[:limit]


def alternatives_message(point: PointSummary, alternatives: list[PointSummary]) -> str:
    risk = point.risk or classify_point_risk(point)
    if not alternatives:
        if risk.level in {"risky", "critical"}:
            return "Nie znaleziono wyraźnie lepszej alternatywy w wybranym promieniu."
        return "Ten punkt wygląda wystarczająco dobrze. Nie znaleziono lepszej alternatywy w pobliżu."

    best = alternatives[0]
    if risk.level in {"risky", "critical"}:
        return f"Ten punkt wygląda ryzykownie. Najlepsza alternatywa w pobliżu to {best.name}."
    return f"Znaleźliśmy też dobrą alternatywę w pobliżu: {best.name}."


def plan_b_message(point: PointSummary, alternatives: list[PointSummary]) -> str | None:
    risk = point.risk or classify_point_risk(point)
    report_signal = point.report_summary.signal if point.report_summary else "none"
    needs_plan_b = risk.level in {"risky", "critical"} or report_signal in {"multiple", "heavy"}
    if not needs_plan_b:
        return None
    if not alternatives:
        return "Nie znaleziono dobrego Planu B w wybranym promieniu."
    return f"Plan B: wybierz {alternatives[0].name}, jeśli chcesz uniknąć ryzyka."


def _with_report_floor(risk: PointRisk, summary: ReportSummary | None) -> PointRisk:
    if summary is None or summary.signal == "none":
        return risk

    floor = summary.ai_risk_floor if summary.ai_risk_floor != "none" else None
    floors = {
        "recent": "watch",
        "multiple": "risky",
        "heavy": "critical",
    }
    if floor is None and (summary.analysis_count == 0 or summary.analysis_pending_count > 0):
        floor = floors.get(summary.signal)
    if floor is None or RISK_ORDER[floor] <= RISK_ORDER.get(risk.level, 0):
        return risk

    labels = {
        "watch": "Uwaga",
        "risky": "Ryzyko",
        "critical": "Krytyczny",
    }
    messages = {
        "watch": "AI lub świeże zgłoszenie wskazuje lekki problem. Sprawdź szczegóły przed wyjściem.",
        "risky": "AI oceniło świeże zgłoszenia jako realne ryzyko. Warto wybrać Plan B.",
        "critical": "AI oceniło świeże zgłoszenia jako poważny problem. Lepiej wybierz alternatywę.",
    }
    return PointRisk(
        level=floor,
        label=labels[floor],
        message=messages[floor],
        reasons=[*risk.reasons, summary.label, *(_community_reasons(summary))],
    )


def _community_reasons(summary: ReportSummary) -> list[str]:
    reasons: list[str] = []
    if summary.community_penalty > 0:
        reasons.append(f"Kara zgłoszeń: -{summary.community_penalty} pkt")
    if summary.problem_score_24h > 0:
        reasons.append(f"Problem score 24h: {summary.problem_score_24h}/100")
    return reasons


def _recommended_point(items: list[PointSummary]) -> PointSummary | None:
    candidates = [
        item
        for item in items
        if item.status == "Operating"
        and item.risk is not None
        and item.risk.level in {"ok", "watch"}
    ]
    if not candidates:
        return None

    return sorted(
        candidates,
        key=lambda item: (
            RISK_ORDER.get(item.risk.level if item.risk else "critical", 99),
            -item.score,
            item.distance_m if item.distance_m is not None else 10**9,
        ),
    )[0]
