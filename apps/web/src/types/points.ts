export type Coordinates = {
  lat: number;
  lng: number;
};

export type PointSummary = {
  id: string;
  name: string;
  country: string;
  status: string | null;
  distance_m: number | null;
  address: string | null;
  city: string | null;
  province: string | null;
  post_code: string | null;
  coordinates: Coordinates;
  score: number;
  grade: "excellent" | "good" | "fair" | "weak" | "critical" | string;
  reasons: string[];
  warnings: string[];
  location_247: boolean;
  easy_access_zone: boolean;
  physical_type: string | null;
  image_url: string | null;
  functions: string[];
  reliability?: ReliabilitySummary | null;
  history_adjustment?: number | null;
  history_reasons?: string[];
  history_warnings?: string[];
  risk?: PointRisk | null;
  report_summary?: ReportSummary | null;
  base_score?: number | null;
  community_penalty: number;
  problem_score_24h: number;
  problem_reasons: string[];
};

export type PointRisk = {
  level: "ok" | "watch" | "risky" | "critical" | string;
  label: string;
  message: string;
  reasons: string[];
};

export type ReportSummary = {
  signal: "none" | "recent" | "multiple" | "heavy" | string;
  label: string;
  message: string;
  count_24h: number;
  count_window: number;
  window_days: number;
  reasons: Record<string, number>;
  latest_report_at: string | null;
  analysis_count: number;
  analysis_pending_count: number;
  problem_score_24h: number;
  max_severity_24h: number;
  community_penalty: number;
  ai_risk_floor: "none" | "watch" | "risky" | "critical" | string;
  analysis_provider: string | null;
  analysis_mode: string | null;
  analysis_model: string | null;
};

export type ReliabilitySummary = {
  label: "brak historii" | "stabilny" | "raczej stabilny" | "niestabilny" | "problem" | string;
  snapshot_count: number;
  uptime_ratio: number | null;
  status_changes: number;
  last_problem_at: string | null;
};

export type PointHistoryItem = {
  collected_at: string;
  status: string | null;
  locker_availability_status: string | null;
  score: number;
  grade: string;
};

export type PointStatusEventItem = {
  detected_at: string;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  from_locker_availability_status: string | null;
  to_locker_availability_status: string | null;
};

export type PointHistoryResponse = {
  country: string;
  name: string;
  window_days: number;
  reliability: ReliabilitySummary;
  timeline: PointHistoryItem[];
  events: PointStatusEventItem[];
};

export type PointSearchResponse = {
  query: {
    lat: number;
    lng: number;
    radius_m: number;
    country: string;
    type: string;
    functions: string[];
    open_24_7: boolean | null;
    easy_access: boolean | null;
    min_score: number | null;
  };
  count: number;
  upstream_count: number | null;
  items: PointSummary[];
  insights: {
    operating: number;
    availability_no_data: number;
    open_24_7: number;
    easy_access: number;
  };
  alerts: SearchAlert[];
};

export type SearchAlert = {
  severity: "info" | "warning" | "critical" | string;
  title: string;
  message: string;
  affected_count: number;
  recommended_point_id: string | null;
};

export type PointAlternativesResponse = {
  point: PointSummary;
  risk: PointRisk;
  alternatives: PointSummary[];
  message: string;
  plan_b_message: string | null;
};

export type ReportReason =
  | "not_working"
  | "full"
  | "screen_problem"
  | "access_problem"
  | "other";

export type UserReportCreate = {
  reason: ReportReason;
  comment: string;
  photos?: UserReportPhoto[];
  lat?: number;
  lng?: number;
};

export type UserReportPhoto = {
  file_name: string;
  content_type: string;
  size_bytes: number;
  data_url: string;
};

export type UserReportAnalysis = {
  status: "pending" | "ok" | "failed" | string;
  severity: number;
  confidence: number;
  category: string;
  is_actionable: boolean;
  spam_likelihood: number;
  photo_evidence: "none" | "weak" | "strong" | string;
  recommended_risk_floor: "none" | "watch" | "risky" | "critical" | string;
  score_penalty: number;
  summary: string;
  evidence: string[];
  model_name: string;
  prompt_version: string;
  provider: "rules" | "litellm" | string;
  analysis_mode: "rules" | "litellm" | "rules_fallback" | string;
  used_images: boolean;
  created_at: string;
  finished_at: string | null;
  error: string | null;
};

export type UserReportResponse = {
  id: string;
  country: string;
  name: string;
  reason: string;
  comment: string;
  photos: UserReportPhoto[];
  source: string;
  created_at: string;
  summary: ReportSummary;
  analysis_status: "pending" | "ok" | "failed" | string;
  analysis: UserReportAnalysis | null;
};

export type AdminReportItem = {
  id: string;
  country: string;
  name: string;
  reason: string;
  comment: string;
  photos_count: number;
  source: string;
  created_at: string;
  point_address: string | null;
  analysis_status: "pending" | "ok" | "failed" | string | null;
  analysis: UserReportAnalysis | null;
};

export type AdminReportListResponse = {
  count: number;
  items: AdminReportItem[];
};

export type AdminDeleteReportResponse = {
  deleted: boolean;
  report_id: string;
};

export type GeocodeResponse = {
  query: string;
  display_name: string;
  coordinates: Coordinates;
};

export type GeocodeSuggestion = {
  display_name: string;
  coordinates: Coordinates;
};

export type GeocodeSuggestionsResponse = {
  query: string;
  count: number;
  items: GeocodeSuggestion[];
};

export type SearchFilters = {
  lat: number;
  lng: number;
  radiusM: number;
  limit: number;
  functions: string[];
  open247: boolean;
  easyAccess: boolean;
  minScore: number;
};
