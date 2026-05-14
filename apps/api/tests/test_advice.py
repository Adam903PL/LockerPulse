from locker_pulse_api.schemas import Coordinates, PointSummary, ReliabilitySummary, ReportSummary
from locker_pulse_api.services.advice import classify_point_risk, select_alternatives


def point(
    *,
    name: str = "WAW1",
    status: str = "Operating",
    score: int = 90,
    reliability_label: str = "stabilny",
    distance_m: int = 100,
    report_signal: str = "none",
    report_count_24h: int = 0,
) -> PointSummary:
    return PointSummary(
        id=f"PL:{name}",
        name=name,
        country="PL",
        status=status,
        distance_m=distance_m,
        address="Testowa 1",
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
        functions=["parcel_collect", "parcel_send"],
        reliability=ReliabilitySummary(
            label=reliability_label,
            snapshot_count=5 if reliability_label != "brak historii" else 0,
            uptime_ratio=1.0 if reliability_label != "brak historii" else None,
            status_changes=0,
            last_problem_at=None,
        ),
        report_summary=ReportSummary(
            signal=report_signal,
            label="Dużo zgłoszeń dzisiaj" if report_signal == "heavy" else "Brak zgłoszeń",
            message="",
            count_24h=report_count_24h,
            count_window=report_count_24h,
            window_days=7,
        ),
    )


def with_risk(item: PointSummary) -> PointSummary:
    return item.model_copy(update={"risk": classify_point_risk(item)})


def test_disabled_point_is_critical():
    risk = classify_point_risk(point(status="Disabled", score=70))

    assert risk.level == "critical"


def test_problem_reliability_is_critical():
    risk = classify_point_risk(point(reliability_label="problem", score=80))

    assert risk.level == "critical"


def test_unstable_history_is_risky():
    risk = classify_point_risk(point(reliability_label="niestabilny", score=80))

    assert risk.level == "risky"


def test_missing_history_is_watch_not_critical():
    risk = classify_point_risk(point(reliability_label="brak historii", score=90))

    assert risk.level == "watch"


def test_fresh_reports_raise_risk_floor():
    assert classify_point_risk(point(score=90, report_signal="recent", report_count_24h=1)).level == "watch"
    assert classify_point_risk(point(score=90, report_signal="multiple", report_count_24h=2)).level == "risky"
    assert classify_point_risk(point(score=90, report_signal="heavy", report_count_24h=4)).level == "critical"


def test_ai_report_floor_raises_risk_even_with_one_report():
    item = point(score=90, report_signal="recent", report_count_24h=1)
    item.report_summary.ai_risk_floor = "risky"
    item.report_summary.analysis_count = 1
    item.report_summary.community_penalty = 22
    item.report_summary.problem_score_24h = 66

    risk = classify_point_risk(item)

    assert risk.level == "risky"
    assert "Kara zgłoszeń" in " ".join(risk.reasons)


def test_alternatives_exclude_current_and_pick_best_stable_candidate():
    current = with_risk(point(name="BAD", status="Disabled", score=20))
    candidates = [
        current,
        with_risk(point(name="LOW", score=55, distance_m=50)),
        with_risk(point(name="BEST", score=95, distance_m=300)),
        with_risk(point(name="NEAR", score=88, distance_m=80)),
    ]

    alternatives = select_alternatives(current, candidates, limit=2)

    assert [item.name for item in alternatives] == ["BEST", "NEAR"]
