from datetime import datetime, timezone

import pytest

from locker_pulse_api.services.report_triage import ReportTriageService
from locker_pulse_api.services.report_triage_engines import (
    LiteLLMTriageEngine,
    ReportTriageEngineError,
    ReportTriageEngineResult,
    RuleBasedTriageEngine,
    build_report_triage_engine,
)
from locker_pulse_api.schemas import UserReportAnalysisResult


class FakeEngine:
    provider = "litellm"
    analysis_mode = "litellm"
    model_name = "openai/gpt-test"

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0
        self.used_images = None

    async def analyze(self, **kwargs):
        self.calls += 1
        self.used_images = kwargs["image_data_urls"]
        if self.error:
            raise self.error
        return ReportTriageEngineResult(
            result=UserReportAnalysisResult.model_validate(self.result),
            raw_response=self.result,
            provider=self.provider,
            analysis_mode=self.analysis_mode,
            model_name=self.model_name,
            used_images=bool(kwargs["image_data_urls"]),
        )


class FakeTriageRepository:
    def __init__(self):
        self.report = {
            "id": "report_1",
            "country": "PL",
            "name": "SYZ01M",
            "reason": "screen_problem",
            "comment": "Ekran nie reaguje i nie mogę odebrać paczki.",
            "photos": [
                {
                    "file_name": "screen.png",
                    "content_type": "image/png",
                    "size_bytes": 128,
                    "data_url": "data:image/png;base64,aaaaaaaaaaaaaaaaaaaaaaaa",
                }
            ],
            "createdAt": datetime.now(timezone.utc),
            "point": {"country": "PL", "name": "SYZ01M", "status": "Operating"},
        }
        self.saved_success = None
        self.saved_failure = None
        self.pending_created = False

    async def get_user_report(self, **kwargs):
        return self.report

    async def create_report_analysis_pending(self, **kwargs):
        self.pending_created = True
        return {"status": "pending", **kwargs}

    async def save_report_analysis_success(self, **kwargs):
        self.saved_success = kwargs
        return kwargs

    async def save_report_analysis_failure(self, **kwargs):
        self.saved_failure = kwargs
        return kwargs

    async def get_pending_report_ids(self, **kwargs):
        return ["report_1"]


def service(repository, engine):
    return ReportTriageService(
        point_repository=repository,
        triage_engine=engine,
        prompt_version="report-triage-v1",
    )


def model_result(**overrides):
    payload = {
        "severity": 80,
        "confidence": 0.82,
        "category": "screen_problem",
        "is_actionable": True,
        "spam_likelihood": 0,
        "photo_evidence": "strong",
        "recommended_risk_floor": "risky",
        "score_penalty": 20,
        "summary": "Ekran prawdopodobnie nie działa.",
        "evidence": ["Komentarz mówi o ekranie"],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_triage_validates_model_json_and_saves_penalty():
    repository = FakeTriageRepository()
    engine = FakeEngine(result=model_result())

    await service(repository, engine).analyze_report(report_id="report_1")

    assert repository.pending_created is True
    assert repository.saved_success["severity"] == 80
    assert repository.saved_success["score_penalty"] == 20
    assert repository.saved_success["provider"] == "litellm"
    assert repository.saved_success["analysis_mode"] == "litellm"
    assert repository.saved_success["used_images"] is True
    assert engine.calls == 1


@pytest.mark.asyncio
async def test_triage_spam_gets_zero_penalty():
    repository = FakeTriageRepository()
    engine = FakeEngine(
        result=model_result(
            severity=90,
            confidence=0.9,
            category="spam",
            is_actionable=False,
            spam_likelihood=0.95,
            recommended_risk_floor="none",
            score_penalty=0,
        )
    )

    await service(repository, engine).analyze_report(report_id="report_1")

    assert repository.saved_success["score_penalty"] == 0
    assert repository.saved_success["recommended_risk_floor"] == "none"


@pytest.mark.asyncio
async def test_triage_model_failure_saves_rules_fallback_success():
    repository = FakeTriageRepository()
    engine = FakeEngine(error=ReportTriageEngineError("model offline"))

    await service(repository, engine).analyze_report(report_id="report_1")

    assert repository.saved_failure is None
    assert repository.saved_success["provider"] == "rules"
    assert repository.saved_success["analysis_mode"] == "rules_fallback"
    assert repository.saved_success["score_penalty"] == 10
    assert "model offline" in repository.saved_success["error"]


@pytest.mark.asyncio
async def test_rule_engine_scores_each_report_category():
    expected = {
        "not_working": (78, 20, "risky"),
        "full": (64, 10, "risky"),
        "screen_problem": (58, 10, "risky"),
        "access_problem": (55, 10, "risky"),
        "other": (35, 5, "watch"),
    }

    for reason, (severity, penalty, risk_floor) in expected.items():
        report = {"reason": reason, "comment": "Opis problemu ma wystarczającą długość.", "photos": []}
        triage = await RuleBasedTriageEngine().analyze(report=report, prompt="", image_data_urls=[])

        assert triage.result.severity == severity
        assert triage.result.score_penalty == penalty
        assert triage.result.recommended_risk_floor == risk_floor


@pytest.mark.asyncio
async def test_rule_engine_safety_keywords_raise_critical():
    report = {"reason": "other", "comment": "Wystają kable i iskry, to wygląda niebezpiecznie.", "photos": []}
    triage = await RuleBasedTriageEngine().analyze(report=report, prompt="", image_data_urls=[])

    assert triage.result.category == "safety_issue"
    assert triage.result.severity == 90
    assert triage.result.score_penalty == 30
    assert triage.result.recommended_risk_floor == "critical"


def test_engine_factory_uses_rules_without_model():
    engine = build_report_triage_engine(
        provider="auto",
        model_name="",
        api_base=None,
        timeout_seconds=60,
        allow_cloud_photos=False,
        local_model_prefixes=("ollama/", "ollama_chat/", "local/"),
    )

    assert isinstance(engine, RuleBasedTriageEngine)


def test_engine_factory_allows_images_only_for_local_or_explicit_cloud_consent():
    local = build_report_triage_engine(
        provider="litellm",
        model_name="ollama_chat/gemma3:4b",
        api_base="http://127.0.0.1:11434",
        timeout_seconds=60,
        allow_cloud_photos=False,
        local_model_prefixes=("ollama/", "ollama_chat/", "local/"),
    )
    cloud = build_report_triage_engine(
        provider="litellm",
        model_name="openai/gpt-4o-mini",
        api_base=None,
        timeout_seconds=60,
        allow_cloud_photos=False,
        local_model_prefixes=("ollama/", "ollama_chat/", "local/"),
    )
    cloud_with_consent = build_report_triage_engine(
        provider="litellm",
        model_name="openai/gpt-4o-mini",
        api_base=None,
        timeout_seconds=60,
        allow_cloud_photos=True,
        local_model_prefixes=("ollama/", "ollama_chat/", "local/"),
    )

    assert isinstance(local, LiteLLMTriageEngine)
    assert local._allow_images is True
    assert isinstance(cloud, LiteLLMTriageEngine)
    assert cloud._allow_images is False
    assert isinstance(cloud_with_consent, LiteLLMTriageEngine)
    assert cloud_with_consent._allow_images is True
