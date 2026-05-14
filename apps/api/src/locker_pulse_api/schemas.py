from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ReportReason = Literal[
    "not_working",
    "full",
    "screen_problem",
    "access_problem",
    "other",
]
ReportAnalysisCategory = Literal[
    "not_working",
    "full",
    "screen_problem",
    "access_problem",
    "location_issue",
    "safety_issue",
    "damaged",
    "vandalism",
    "unclear",
    "spam",
    "other",
]
ReportPhotoEvidence = Literal["none", "weak", "strong"]
ReportRiskFloor = Literal["none", "watch", "risky", "critical"]
ReportAnalysisStatus = Literal["pending", "ok", "failed"]
ReportAnalysisProvider = Literal["rules", "litellm"]
ReportAnalysisMode = Literal["rules", "litellm", "rules_fallback"]


class Coordinates(BaseModel):
    lat: float
    lng: float


class ScoreBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    grade: str
    reasons: list[str]
    warnings: list[str]


class ReliabilitySummary(BaseModel):
    label: str
    snapshot_count: int
    uptime_ratio: float | None
    status_changes: int
    last_problem_at: datetime | None


class PointRisk(BaseModel):
    level: str
    label: str
    message: str
    reasons: list[str] = Field(default_factory=list)


class UserReportPhoto(BaseModel):
    file_name: str = Field(min_length=1, max_length=160)
    content_type: str = Field(pattern=r"^image/(jpeg|png|webp)$")
    size_bytes: int = Field(ge=1, le=1_500_000)
    data_url: str = Field(min_length=20, max_length=2_200_000)


class UserReportAnalysisResult(BaseModel):
    severity: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    category: ReportAnalysisCategory
    is_actionable: bool
    spam_likelihood: float = Field(ge=0, le=1)
    photo_evidence: ReportPhotoEvidence
    recommended_risk_floor: ReportRiskFloor
    score_penalty: int = Field(ge=0, le=30)
    summary: str = Field(min_length=1, max_length=180)
    evidence: list[str] = Field(default_factory=list, max_length=4)


class UserReportAnalysisPublic(UserReportAnalysisResult):
    status: ReportAnalysisStatus
    model_name: str
    prompt_version: str
    provider: ReportAnalysisProvider = "rules"
    analysis_mode: ReportAnalysisMode = "rules"
    used_images: bool = False
    created_at: datetime
    finished_at: datetime | None = None
    error: str | None = None


class ReportSummary(BaseModel):
    signal: str
    label: str
    message: str
    count_24h: int
    count_window: int
    window_days: int
    reasons: dict[str, int] = Field(default_factory=dict)
    latest_report_at: datetime | None = None
    has_demo_data: bool = False
    analysis_count: int = 0
    analysis_pending_count: int = 0
    problem_score_24h: int = 0
    max_severity_24h: int = 0
    community_penalty: int = 0
    ai_risk_floor: ReportRiskFloor = "none"
    analysis_provider: str | None = None
    analysis_mode: str | None = None
    analysis_model: str | None = None


class PointSummary(BaseModel):
    id: str
    name: str
    country: str
    status: str | None
    distance_m: int | None
    address: str | None
    city: str | None
    province: str | None
    post_code: str | None
    coordinates: Coordinates
    score: int = Field(ge=0, le=100)
    grade: str
    reasons: list[str]
    warnings: list[str]
    location_247: bool
    easy_access_zone: bool
    physical_type: str | None
    image_url: str | None
    functions: list[str]
    reliability: ReliabilitySummary | None = None
    history_adjustment: int | None = None
    history_reasons: list[str] = Field(default_factory=list)
    history_warnings: list[str] = Field(default_factory=list)
    risk: PointRisk | None = None
    report_summary: ReportSummary | None = None
    base_score: int | None = None
    community_penalty: int = 0
    problem_score_24h: int = 0
    problem_reasons: list[str] = Field(default_factory=list)


class PointHistoryItem(BaseModel):
    collected_at: datetime
    status: str | None
    locker_availability_status: str | None
    score: int
    grade: str


class PointStatusEventItem(BaseModel):
    detected_at: datetime
    event_type: str
    from_status: str | None
    to_status: str | None
    from_locker_availability_status: str | None
    to_locker_availability_status: str | None


class PointHistoryResponse(BaseModel):
    country: str
    name: str
    window_days: int
    is_demo: bool = False
    demo_note: str | None = None
    reliability: ReliabilitySummary
    timeline: list[PointHistoryItem]
    events: list[PointStatusEventItem]


class SearchQueryEcho(BaseModel):
    lat: float
    lng: float
    radius_m: int
    country: str
    type: str
    functions: list[str]
    open_24_7: bool | None
    easy_access: bool | None
    min_score: int | None
    demo: bool = False


class SearchInsights(BaseModel):
    operating: int
    availability_no_data: int
    open_24_7: int
    easy_access: int


class SearchAlert(BaseModel):
    severity: str
    title: str
    message: str
    affected_count: int
    recommended_point_id: str | None = None


class PointSearchResponse(BaseModel):
    query: SearchQueryEcho
    count: int
    upstream_count: int | None
    items: list[PointSummary]
    insights: SearchInsights
    alerts: list[SearchAlert] = Field(default_factory=list)


class PointAlternativesResponse(BaseModel):
    point: PointSummary
    risk: PointRisk
    alternatives: list[PointSummary]
    message: str
    plan_b_message: str | None = None


class UserReportCreate(BaseModel):
    reason: ReportReason
    comment: str = Field(min_length=10, max_length=500)
    photos: list[UserReportPhoto] = Field(default_factory=list, max_length=3)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class UserReportResponse(BaseModel):
    id: str
    country: str
    name: str
    reason: str
    comment: str
    photos: list[UserReportPhoto] = Field(default_factory=list)
    source: str
    is_demo: bool
    created_at: datetime
    summary: ReportSummary
    analysis_status: ReportAnalysisStatus = "pending"
    analysis: UserReportAnalysisPublic | None = None


class ReportAnalysisResponse(BaseModel):
    report_id: str
    analysis: UserReportAnalysisPublic | None = None


class AdminReportItem(BaseModel):
    id: str
    country: str
    name: str
    reason: str
    comment: str
    photos_count: int
    source: str
    is_demo: bool
    created_at: datetime
    point_address: str | None = None
    analysis_status: ReportAnalysisStatus | None = None
    analysis: UserReportAnalysisPublic | None = None


class AdminReportListResponse(BaseModel):
    count: int
    items: list[AdminReportItem]


class AdminDeleteReportResponse(BaseModel):
    deleted: bool
    report_id: str


class HealthResponse(BaseModel):
    status: str
    service: str


class GeocodeResponse(BaseModel):
    query: str
    display_name: str
    coordinates: Coordinates


class GeocodeSuggestion(BaseModel):
    display_name: str
    coordinates: Coordinates


class GeocodeSuggestionsResponse(BaseModel):
    query: str
    count: int
    items: list[GeocodeSuggestion]


class ApiErrorResponse(BaseModel):
    detail: str
