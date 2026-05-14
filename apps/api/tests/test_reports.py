from datetime import datetime, timedelta, timezone

import pytest

from locker_pulse_api.schemas import UserReportCreate
from locker_pulse_api.services.reports import (
    ReportPointNotFound,
    ReportService,
    build_report_summary,
    calculate_score_penalty,
)


def analysis(
    *,
    severity=80,
    confidence=0.8,
    status="ok",
    category="screen_problem",
    is_actionable=True,
    spam_likelihood=0.0,
    recommended_risk_floor="risky",
    score_penalty=20,
):
    return {
        "status": status,
        "severity": severity,
        "confidence": confidence,
        "category": category,
        "isActionable": is_actionable,
        "spamLikelihood": spam_likelihood,
        "recommendedRiskFloor": recommended_risk_floor,
        "scorePenalty": score_penalty,
        "photoEvidence": "none",
        "summary": "Problem z ekranem.",
        "evidence": ["Komentarz wskazuje problem"],
        "modelName": "gemma3:4b",
        "promptVersion": "report-triage-v1",
        "createdAt": datetime.now(timezone.utc),
    }


def report(reason="not_working", hours_ago=1, is_demo=False, report_analysis=None):
    return {
        "reason": reason,
        "createdAt": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        "isDemo": is_demo,
        "analysis": report_analysis,
    }


def test_report_summary_without_reports_is_none_signal():
    summary = build_report_summary(reports=[], days=7)

    assert summary.signal == "none"
    assert summary.count_24h == 0
    assert summary.label == "Brak zgłoszeń"


def test_report_summary_classifies_recent_multiple_and_heavy():
    assert build_report_summary(reports=[report()], days=7).signal == "recent"
    assert build_report_summary(reports=[report(), report()], days=7).signal == "multiple"
    assert build_report_summary(reports=[report(), report(), report(), report()], days=7).signal == "heavy"


def test_old_reports_do_not_raise_24h_signal_aggressively():
    summary = build_report_summary(reports=[report(hours_ago=48), report(hours_ago=72)], days=7)

    assert summary.signal == "none"
    assert summary.count_24h == 0
    assert summary.count_window == 2


def test_ai_analysis_summary_adds_problem_score_and_penalty():
    summary = build_report_summary(
        reports=[
            report(report_analysis=analysis(severity=80, confidence=0.8, score_penalty=20)),
            report(report_analysis=analysis(severity=70, confidence=0.7, score_penalty=20)),
        ],
        days=7,
    )

    assert summary.analysis_count == 2
    assert summary.problem_score_24h > 0
    assert summary.community_penalty == 35
    assert summary.ai_risk_floor == "risky"


def test_score_penalty_ignores_spam_and_low_confidence():
    assert calculate_score_penalty(
        severity=90,
        confidence=0.9,
        category="spam",
        spam_likelihood=0.95,
        is_actionable=False,
    ) == 0
    assert calculate_score_penalty(
        severity=80,
        confidence=0.2,
        category="screen_problem",
        spam_likelihood=0,
        is_actionable=True,
    ) == 0
    assert calculate_score_penalty(
        severity=80,
        confidence=0.8,
        category="screen_problem",
        spam_likelihood=0,
        is_actionable=True,
    ) == 20


class FakeReportRepository:
    def __init__(self, point_exists=True):
        self.point_exists = point_exists
        self.created = []

    async def create_user_report(self, **kwargs):
        if not self.point_exists:
            return None
        payload = {
            "id": "report_1",
            "createdAt": datetime.now(timezone.utc),
            "isDemo": False,
            **kwargs,
        }
        self.created.append(payload)
        return payload

    async def create_report_analysis_pending(self, **kwargs):
        self.created[-1]["analysis"] = {
            "status": "pending",
            "severity": 0,
            "confidence": 0,
            "category": "unclear",
            "isActionable": False,
            "spamLikelihood": 0,
            "recommendedRiskFloor": "none",
            "scorePenalty": 0,
        }
        return self.created[-1]["analysis"]

    async def get_user_reports_since(self, **kwargs):
        return self.created


@pytest.mark.asyncio
async def test_report_service_creates_report_and_summary():
    repository = FakeReportRepository()
    service = ReportService(repository)

    created = await service.create_report(
        country="PL",
        name="SYZ01M",
        payload=UserReportCreate(
            reason="screen_problem",
            comment="Ekran nie reaguje na dotyk.",
            photos=[
                {
                    "file_name": "ekran.png",
                    "content_type": "image/png",
                    "size_bytes": 128,
                    "data_url": "data:image/png;base64,aaaaaaaaaaaaaaaaaaaaaaaa",
                }
            ],
            lat=51.0808,
            lng=22.4416,
        ),
    )

    assert created.reason == "screen_problem"
    assert created.photos[0].file_name == "ekran.png"
    assert created.summary.signal == "recent"
    assert repository.created[0]["photos"][0]["content_type"] == "image/png"
    assert repository.created[0]["comment"] == "Ekran nie reaguje na dotyk."


@pytest.mark.asyncio
async def test_report_service_raises_when_point_is_missing():
    service = ReportService(FakeReportRepository(point_exists=False))

    with pytest.raises(ReportPointNotFound):
        await service.create_report(
            country="PL",
            name="MISSING",
            payload=UserReportCreate(reason="other", comment="Nie mogę znaleźć tego punktu."),
        )
