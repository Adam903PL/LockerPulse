import type {
  AdminDeleteReportResponse,
  AdminReportListResponse,
  GeocodeResponse,
  GeocodeSuggestionsResponse,
  PointAlternativesResponse,
  PointHistoryResponse,
  PointSearchResponse,
  PointSummary,
  SearchFilters,
  UserReportAnalysis,
  UserReportCreate,
  UserReportResponse,
} from "@/types/points";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export function buildSearchUrl(filters: SearchFilters) {
  const params = new URLSearchParams({
    lat: String(filters.lat),
    lng: String(filters.lng),
    radius_m: String(filters.radiusM),
    limit: String(filters.limit),
    min_score: String(filters.minScore),
    country: "PL",
    type: "parcel_locker_only",
  });

  if (filters.functions.length > 0) {
    params.set("functions", filters.functions.join(","));
  }
  if (filters.open247) {
    params.set("open_24_7", "true");
  }
  if (filters.easyAccess) {
    params.set("easy_access", "true");
  }
  return `${API_BASE_URL}/api/v1/points/search?${params.toString()}`;
}

export async function fetchPointSearch(url: string): Promise<PointSearchResponse> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export function buildPointUrl(
  country: string,
  name: string,
  context?: { lat?: string; lng?: string; radiusM?: number },
) {
  const params = new URLSearchParams();
  if (context?.lat && context.lng) {
    params.set("lat", context.lat);
    params.set("lng", context.lng);
    params.set("radius_m", String(context.radiusM ?? 3000));
  }
  const suffix = params.toString();
  return `${API_BASE_URL}/api/v1/points/${encodeURIComponent(country)}/${encodeURIComponent(name)}${suffix ? `?${suffix}` : ""}`;
}

export async function fetchPointDetails(url: string): Promise<PointSummary> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export function buildPointHistoryUrl(country: string, name: string, days = 7) {
  const params = new URLSearchParams({ days: String(days) });
  return `${API_BASE_URL}/api/v1/points/${encodeURIComponent(country)}/${encodeURIComponent(name)}/history?${params.toString()}`;
}

export async function fetchPointHistory(url: string): Promise<PointHistoryResponse> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export function buildPointAlternativesUrl(
  country: string,
  name: string,
  context: { lat: string; lng: string; radiusM?: number; limit?: number },
) {
  const params = new URLSearchParams({
    lat: context.lat,
    lng: context.lng,
    radius_m: String(context.radiusM ?? 3000),
    limit: String(context.limit ?? 3),
  });
  return `${API_BASE_URL}/api/v1/points/${encodeURIComponent(country)}/${encodeURIComponent(name)}/alternatives?${params.toString()}`;
}

export async function fetchPointAlternatives(url: string): Promise<PointAlternativesResponse> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export function buildReportSummaryUrl(country: string, name: string, days = 7) {
  const params = new URLSearchParams({ days: String(days) });
  return `${API_BASE_URL}/api/v1/points/${encodeURIComponent(country)}/${encodeURIComponent(name)}/reports/summary?${params.toString()}`;
}

export function buildCreateReportUrl(country: string, name: string) {
  return `${API_BASE_URL}/api/v1/points/${encodeURIComponent(country)}/${encodeURIComponent(name)}/reports`;
}

export function buildReportAnalysisUrl(reportId: string) {
  return `${API_BASE_URL}/api/v1/reports/${encodeURIComponent(reportId)}/analysis`;
}

export async function fetchReportAnalysis(url: string): Promise<{ report_id: string; analysis: UserReportAnalysis | null }> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export async function createUserReport(
  country: string,
  name: string,
  payload: UserReportCreate,
): Promise<UserReportResponse> {
  const response = await fetch(buildCreateReportUrl(country, name), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export async function geocodeAddress(query: string): Promise<GeocodeResponse> {
  const params = new URLSearchParams({ q: query });
  const response = await fetch(`${API_BASE_URL}/api/v1/geocode?${params.toString()}`);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Address lookup failed with ${response.status}`);
  }
  return response.json();
}

export async function fetchGeocodeSuggestions(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodeSuggestionsResponse> {
  const params = new URLSearchParams({ q: query, limit: "5" });
  const response = await fetch(`${API_BASE_URL}/api/v1/geocode/suggest?${params.toString()}`, {
    signal,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Address suggestions failed with ${response.status}`);
  }
  return response.json();
}

export function buildAdminReportsUrl(options?: { limit?: number }) {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 100),
  });
  return `${API_BASE_URL}/api/v1/admin/reports?${params.toString()}`;
}

export async function fetchAdminReports([url, token]: [string, string]): Promise<AdminReportListResponse> {
  const response = await fetch(url, {
    headers: adminHeaders(token),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export async function deleteAdminReport(reportId: string, token: string): Promise<AdminDeleteReportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/reports/${encodeURIComponent(reportId)}`, {
    method: "DELETE",
    headers: adminHeaders(token),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

function adminHeaders(token: string): Record<string, string> {
  const trimmed = token.trim();
  return trimmed ? { "X-Admin-Token": trimmed } : {};
}
