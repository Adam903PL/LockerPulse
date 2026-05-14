import json
from dataclasses import dataclass
from typing import Any, Protocol

from locker_pulse_api.schemas import UserReportAnalysisResult
from locker_pulse_api.services.reports import calculate_score_penalty


class ReportTriageEngineError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportTriageEngineResult:
    result: UserReportAnalysisResult
    raw_response: dict[str, Any]
    provider: str
    analysis_mode: str
    model_name: str
    used_images: bool = False
    error: str | None = None


class ReportTriageEngine(Protocol):
    provider: str
    analysis_mode: str
    model_name: str

    async def analyze(
        self,
        *,
        report: Any,
        prompt: str,
        image_data_urls: list[str],
    ) -> ReportTriageEngineResult:
        ...


class RuleBasedTriageEngine:
    provider = "rules"

    def __init__(self, *, analysis_mode: str = "rules", model_name: str = "rules", error: str | None = None) -> None:
        self.analysis_mode = analysis_mode
        self.model_name = model_name
        self._error = error

    async def analyze(
        self,
        *,
        report: Any,
        prompt: str,
        image_data_urls: list[str],
    ) -> ReportTriageEngineResult:
        del prompt
        reason = str(_field(report, "reason") or "other")
        comment = str(_field(report, "comment") or "")
        result = _rule_result(reason=reason, comment=comment, has_photos=bool(image_data_urls))
        return ReportTriageEngineResult(
            result=result,
            raw_response={
                "source": "rule_based",
                "reason": reason,
                "matched_safety_keywords": _matched_safety_keywords(comment),
                "fallback_error": self._error,
            },
            provider=self.provider,
            analysis_mode=self.analysis_mode,
            model_name=self.model_name,
            used_images=False,
            error=self._error,
        )


class LiteLLMTriageEngine:
    provider = "litellm"
    analysis_mode = "litellm"

    def __init__(
        self,
        *,
        model_name: str,
        api_base: str | None,
        timeout_seconds: float,
        allow_images: bool,
    ) -> None:
        self.model_name = model_name
        self._api_base = api_base
        self._timeout_seconds = timeout_seconds
        self._allow_images = allow_images

    async def analyze(
        self,
        *,
        report: Any,
        prompt: str,
        image_data_urls: list[str],
    ) -> ReportTriageEngineResult:
        del report
        used_images = bool(self._allow_images and image_data_urls)
        try:
            raw = await self._generate_json(prompt=prompt, image_data_urls=image_data_urls if used_images else [])
            result = _normalize_result(raw)
        except Exception as exc:  # pragma: no cover - concrete provider failures vary
            raise ReportTriageEngineError(str(exc)) from exc

        return ReportTriageEngineResult(
            result=result,
            raw_response=raw,
            provider=self.provider,
            analysis_mode=self.analysis_mode,
            model_name=self.model_name,
            used_images=used_images,
        )

    async def _generate_json(self, *, prompt: str, image_data_urls: list[str]) -> dict[str, Any]:
        try:
            from litellm import acompletion
        except Exception as exc:  # pragma: no cover - missing optional package in broken envs
            raise ReportTriageEngineError("LiteLLM is not available.") from exc

        messages = [{"role": "user", "content": _message_content(prompt=prompt, image_data_urls=image_data_urls)}]
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0,
            "timeout": self._timeout_seconds,
            "response_format": {"type": "json_object"},
            "drop_params": True,
        }
        if self._api_base:
            kwargs["api_base"] = self._api_base
        if self.model_name.startswith(("ollama/", "ollama_chat/")):
            kwargs["format"] = "json"

        response = await acompletion(**kwargs)
        content = _response_content(response)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ReportTriageEngineError("LiteLLM response was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ReportTriageEngineError("LiteLLM response JSON was not an object.")
        return parsed


def build_report_triage_engine(
    *,
    provider: str,
    model_name: str,
    api_base: str | None,
    timeout_seconds: float,
    allow_cloud_photos: bool,
    local_model_prefixes: tuple[str, ...],
) -> ReportTriageEngine:
    selected_provider = provider.strip().lower()
    selected_model = model_name.strip()

    if selected_provider == "rules" or not selected_model:
        return RuleBasedTriageEngine()
    if selected_provider not in {"auto", "litellm"}:
        return RuleBasedTriageEngine(error=f"Unknown provider: {provider}")

    is_local_model = selected_model.startswith(local_model_prefixes)
    return LiteLLMTriageEngine(
        model_name=selected_model,
        api_base=api_base,
        timeout_seconds=timeout_seconds,
        allow_images=allow_cloud_photos or is_local_model,
    )


def _message_content(*, prompt: str, image_data_urls: list[str]) -> str | list[dict[str, Any]]:
    if not image_data_urls:
        return prompt
    return [
        {"type": "text", "text": prompt},
        *[
            {
                "type": "image_url",
                "image_url": {"url": image_data_url},
            }
            for image_data_url in image_data_urls
        ],
    ]


def _response_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError):
        content = None
    if content is None and isinstance(response, dict):
        choices = response.get("choices") or []
        if choices:
            content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise ReportTriageEngineError("LiteLLM response did not contain text content.")
    return content


def _rule_result(*, reason: str, comment: str, has_photos: bool) -> UserReportAnalysisResult:
    safety_keywords = _matched_safety_keywords(comment)
    if safety_keywords:
        return _build_result(
            severity=90,
            confidence=0.86,
            category="safety_issue",
            recommended_risk_floor="critical",
            summary="Zgłoszenie wskazuje możliwy problem bezpieczeństwa przy punkcie.",
            evidence=[f"Wykryto słowa bezpieczeństwa: {', '.join(safety_keywords[:3])}"],
            has_photos=has_photos,
        )

    rules = {
        "not_working": (
            78,
            0.78,
            "not_working",
            "risky",
            "Zgłoszenie wskazuje, że punkt może nie działać poprawnie.",
        ),
        "full": (
            64,
            0.74,
            "full",
            "risky",
            "Zgłoszenie wskazuje problem z dostępnością skrytek.",
        ),
        "screen_problem": (
            58,
            0.72,
            "screen_problem",
            "risky",
            "Zgłoszenie wskazuje problem z ekranem lub obsługą punktu.",
        ),
        "access_problem": (
            55,
            0.72,
            "access_problem",
            "risky",
            "Zgłoszenie wskazuje problem z dostępem do punktu.",
        ),
    }
    severity, confidence, category, risk_floor, summary = rules.get(
        reason,
        (
            35,
            0.65,
            "other",
            "watch",
            "Zgłoszenie jest ogólne, ale warto pokazać lekkie ostrzeżenie.",
        ),
    )
    return _build_result(
        severity=severity,
        confidence=confidence,
        category=category,
        recommended_risk_floor=risk_floor,
        summary=summary,
        evidence=[f"Reguła fallback dla kategorii: {reason}"],
        has_photos=has_photos,
    )


def _build_result(
    *,
    severity: int,
    confidence: float,
    category: str,
    recommended_risk_floor: str,
    summary: str,
    evidence: list[str],
    has_photos: bool,
) -> UserReportAnalysisResult:
    penalty = calculate_score_penalty(
        severity=severity,
        confidence=confidence,
        category=category,
        spam_likelihood=0,
        is_actionable=True,
    )
    if penalty == 0:
        recommended_risk_floor = "none"
    return UserReportAnalysisResult.model_validate(
        {
            "severity": severity,
            "confidence": confidence,
            "category": category,
            "is_actionable": True,
            "spam_likelihood": 0,
            "photo_evidence": "weak" if has_photos else "none",
            "recommended_risk_floor": recommended_risk_floor,
            "score_penalty": penalty,
            "summary": summary,
            "evidence": evidence,
        }
    )


def _normalize_result(raw: dict[str, Any]) -> UserReportAnalysisResult:
    severity = _int_between(raw.get("severity"), 0, 100)
    confidence = _float_between(raw.get("confidence"), 0, 1)
    category = str(raw.get("category") or "unclear")
    is_actionable = bool(raw.get("is_actionable"))
    spam_likelihood = _float_between(raw.get("spam_likelihood"), 0, 1)
    photo_evidence = str(raw.get("photo_evidence") or "none")
    recommended_risk_floor = str(raw.get("recommended_risk_floor") or "none")
    penalty = calculate_score_penalty(
        severity=severity,
        confidence=confidence,
        category=category,
        spam_likelihood=spam_likelihood,
        is_actionable=is_actionable,
    )
    if penalty == 0 and recommended_risk_floor != "none":
        recommended_risk_floor = "none"

    return UserReportAnalysisResult.model_validate(
        {
            "severity": severity,
            "confidence": confidence,
            "category": category,
            "is_actionable": is_actionable,
            "spam_likelihood": spam_likelihood,
            "photo_evidence": photo_evidence,
            "recommended_risk_floor": recommended_risk_floor,
            "score_penalty": penalty,
            "summary": str(raw.get("summary") or "Analiza nie znalazła jednoznacznego problemu.")[:180],
            "evidence": [str(item)[:180] for item in (raw.get("evidence") or [])][:4],
        }
    )


def _matched_safety_keywords(comment: str) -> list[str]:
    text = comment.lower()
    keywords = [
        "niebezpiecznie",
        "niebezpieczny",
        "kable",
        "iskry",
        "iskrzy",
        "zagrożenie",
        "zagrozenie",
        "prąd",
        "prad",
        "ogień",
        "ogien",
        "pożar",
        "pozar",
    ]
    return [keyword for keyword in keywords if keyword in text]


def _field(item: Any, name: str) -> Any:
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _int_between(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))


def _float_between(value: Any, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))
