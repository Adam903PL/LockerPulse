"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, ChevronRight, Loader2, MapPin, Search } from "lucide-react";
import useSWR from "swr";
import { buildSearchUrl, fetchGeocodeSuggestions, fetchPointSearch, geocodeAddress } from "@/lib/api";
import {
  formatDistance,
  pointHref,
  riskClass,
  riskLabel,
  shortAddress,
  statusClass,
  statusLabel,
} from "@/lib/point-display";
import { cn } from "@/lib/utils";
import type {
  Coordinates,
  GeocodeSuggestion,
  PointSearchResponse,
  PointSummary,
  SearchFilters,
} from "@/types/points";
import { MapShell } from "./map-shell";
import { ScoreBadge } from "./score-badge";
import {
  DemoModeSwitch,
  DEMO_SEARCH,
  readPersistedDemoMode,
  writePersistedDemoMode,
} from "./demo-mode-switch";

const DEFAULT_RADIUS_M = 3000;
const DEFAULT_LIMIT = 20;
const DEFAULT_CENTER: Coordinates = { lat: 52.0, lng: 19.0 };
const MIN_ADDRESS_QUERY_LENGTH = 3;
const REALTIME_SEARCH_DELAY_MS = 650;

type LockerPulseAppProps = {
  initialQuery?: string;
  initialCoordinates?: Coordinates | null;
  initialRadiusM?: number;
  initialDemoMode?: boolean;
};

export function LockerPulseApp({
  initialQuery = "",
  initialCoordinates = null,
  initialRadiusM = DEFAULT_RADIUS_M,
  initialDemoMode = false,
}: LockerPulseAppProps) {
  const router = useRouter();
  const initialDemoCoordinates = initialDemoMode && !initialCoordinates
    ? { lat: DEMO_SEARCH.lat, lng: DEMO_SEARCH.lng }
    : null;
  const [demoMode, setDemoMode] = useState(initialDemoMode);
  const [address, setAddress] = useState(initialQuery || (initialDemoCoordinates ? DEMO_SEARCH.query : ""));
  const [resolvedAddress, setResolvedAddress] = useState<string | null>(
    initialQuery || (initialDemoCoordinates ? DEMO_SEARCH.query : null),
  );
  const [addressError, setAddressError] = useState<string | null>(null);
  const [isGeocoding, setIsGeocoding] = useState(false);
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [hasLocation, setHasLocation] = useState(Boolean(initialCoordinates || initialDemoCoordinates));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const realtimeRequestId = useRef(0);
  const lastAppliedRealtimeQuery = useRef(initialQuery || (initialDemoCoordinates ? DEMO_SEARCH.query : ""));
  const hasRestoredPersistedDemoMode = useRef(false);
  const [filters, setFilters] = useState<SearchFilters>({
    lat: initialCoordinates?.lat ?? initialDemoCoordinates?.lat ?? DEFAULT_CENTER.lat,
    lng: initialCoordinates?.lng ?? initialDemoCoordinates?.lng ?? DEFAULT_CENTER.lng,
    radiusM: initialRadiusM,
    limit: DEFAULT_LIMIT,
    functions: [],
    open247: false,
    easyAccess: false,
    minScore: 0,
    demo: initialDemoMode,
  });

  const searchUrl = useMemo(
    () => (hasLocation ? buildSearchUrl(filters) : null),
    [filters, hasLocation],
  );

  const { data, error, isLoading, isValidating } = useSWR(searchUrl, fetchPointSearch, {
    keepPreviousData: true,
    revalidateOnFocus: false,
  });

  const selectedPoint =
    data?.items.find((point) => point.id === selectedId) ?? data?.items[0] ?? null;

  const returnParams = useMemo(() => {
    const params = new URLSearchParams();
    const query = address.trim();
    if (query) {
      params.set("q", query);
    }
    if (hasLocation) {
      params.set("lat", String(filters.lat));
      params.set("lng", String(filters.lng));
      params.set("radius_m", String(filters.radiusM));
    }
    if (demoMode) {
      params.set("demo", "true");
    }
    return params;
  }, [address, demoMode, filters.lat, filters.lng, filters.radiusM, hasLocation]);

  const applyAddressResult = useCallback((
    result: GeocodeSuggestion,
    query: string,
    mode: "push" | "replace",
  ) => {
    const nextRadiusM = filters.radiusM;
    setResolvedAddress(result.display_name);
    setHasLocation(true);
    setSelectedId(null);
    setFilters((current) => ({
      ...current,
      lat: result.coordinates.lat,
      lng: result.coordinates.lng,
      demo: demoMode,
    }));

    const params = new URLSearchParams({
      q: query,
      lat: String(result.coordinates.lat),
      lng: String(result.coordinates.lng),
      radius_m: String(nextRadiusM),
    });
    if (demoMode) {
      params.set("demo", "true");
    }

    const nextUrl = `/app?${params.toString()}`;
    if (mode === "push") {
      router.push(nextUrl);
      return;
    }
    router.replace(nextUrl);
  }, [demoMode, filters.radiusM, router]);

  const handleAddressChange = useCallback((value: string) => {
    setAddress(value);
    setAddressError(null);

    if (value.trim().length < MIN_ADDRESS_QUERY_LENGTH) {
      realtimeRequestId.current += 1;
      setSuggestions([]);
      setSuggestionsOpen(false);
      setIsSuggesting(false);
      setResolvedAddress(null);
      setHasLocation(false);
    }
  }, []);

  const selectSuggestion = useCallback((suggestion: GeocodeSuggestion) => {
    const query = suggestion.display_name;
    lastAppliedRealtimeQuery.current = query;
    setAddress(query);
    setSuggestionsOpen(false);
    setSuggestions([]);
    setAddressError(null);
    applyAddressResult(suggestion, query, "push");
  }, [applyAddressResult]);

  async function searchAddress() {
    const query = address.trim();
    if (query.length < MIN_ADDRESS_QUERY_LENGTH) {
      setAddressError("Wpisz adres, np. Długa 1, Gdańsk.");
      return;
    }

    setIsGeocoding(true);
    setAddressError(null);

    try {
      const result = await geocodeAddress(query);
      lastAppliedRealtimeQuery.current = query;
      setSuggestionsOpen(false);
      setSuggestions([]);
      applyAddressResult(result, query, "push");
    } catch (err) {
      setHasLocation(false);
      setResolvedAddress(null);
      setAddressError(err instanceof Error ? err.message : "Nie znaleziono adresu.");
    } finally {
      setIsGeocoding(false);
    }
  }

  const toggleDemoMode = useCallback((next: boolean) => {
    writePersistedDemoMode(next);
    setDemoMode(next);
    setSelectedId(null);

    if (next) {
      const nextFilters = {
        ...filters,
        lat: hasLocation ? filters.lat : DEMO_SEARCH.lat,
        lng: hasLocation ? filters.lng : DEMO_SEARCH.lng,
        radiusM: hasLocation ? filters.radiusM : DEMO_SEARCH.radiusM,
        demo: true,
      };
      setFilters(nextFilters);
      if (!hasLocation) {
        setAddress(DEMO_SEARCH.query);
        setResolvedAddress(DEMO_SEARCH.query);
        setHasLocation(true);
      }

      const params = new URLSearchParams({
        q: hasLocation ? address.trim() || DEMO_SEARCH.query : DEMO_SEARCH.query,
        lat: String(nextFilters.lat),
        lng: String(nextFilters.lng),
        radius_m: String(nextFilters.radiusM),
        demo: "true",
      });
      router.push(`/app?${params.toString()}`);
      return;
    }

    const nextFilters = { ...filters, demo: false };
    setFilters(nextFilters);
    const params = new URLSearchParams();
    const query = address.trim();
    if (query) {
      params.set("q", query);
    }
    if (hasLocation) {
      params.set("lat", String(nextFilters.lat));
      params.set("lng", String(nextFilters.lng));
      params.set("radius_m", String(nextFilters.radiusM));
    }
    const suffix = params.toString();
    router.push(suffix ? `/app?${suffix}` : "/app");
  }, [address, filters, hasLocation, router]);

  useEffect(() => {
    const query = address.trim();
    if (query.length < MIN_ADDRESS_QUERY_LENGTH || query === lastAppliedRealtimeQuery.current) {
      return;
    }

    const requestId = realtimeRequestId.current + 1;
    realtimeRequestId.current = requestId;
    const controller = new AbortController();

    const timer = window.setTimeout(async () => {
      setIsSuggesting(true);
      try {
        const result = await fetchGeocodeSuggestions(query, controller.signal);
        if (realtimeRequestId.current !== requestId) {
          return;
        }

        setSuggestions(result.items);
        setSuggestionsOpen(result.items.length > 0);

        const bestMatch = result.items[0];
        if (!bestMatch) {
          setHasLocation(false);
          setResolvedAddress(null);
          setAddressError("Nie znaleziono takiego adresu. Spróbuj dopisać miasto.");
          return;
        }

        lastAppliedRealtimeQuery.current = query;
        setAddressError(null);
        applyAddressResult(bestMatch, query, "replace");
      } catch (err) {
        if (controller.signal.aborted || realtimeRequestId.current !== requestId) {
          return;
        }
        setSuggestions([]);
        setSuggestionsOpen(false);
        setAddressError(err instanceof Error ? err.message : "Nie udało się pobrać podpowiedzi.");
      } finally {
        if (realtimeRequestId.current === requestId) {
          setIsSuggesting(false);
        }
      }
    }, REALTIME_SEARCH_DELAY_MS);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [address, applyAddressResult]);

  useEffect(() => {
    if (hasRestoredPersistedDemoMode.current) {
      return;
    }
    hasRestoredPersistedDemoMode.current = true;

    if (initialDemoMode) {
      writePersistedDemoMode(true);
      return;
    }

    if (readPersistedDemoMode()) {
      const timer = window.setTimeout(() => toggleDemoMode(true), 0);
      return () => window.clearTimeout(timer);
    }
  }, [initialDemoMode, toggleDemoMode]);

  return (
    <main className="min-h-screen bg-[#f4f4f2] text-[#1d1d1b]">
      <header className="border-b border-black/10 bg-white">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/app" className="flex items-center gap-3" aria-label="LockerPulse app">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#ffd200] font-black text-[#1d1d1b]">
              LP
            </span>
            <span className="text-lg font-black tracking-normal">LockerPulse</span>
          </Link>
          <div className="flex items-center gap-2">
            <DemoModeSwitch enabled={demoMode} onChange={toggleDemoMode} />
            <span className="rounded-full border border-black/10 bg-[#ffd200] px-3 py-1 text-xs font-bold uppercase text-[#1d1d1b]">
              Beta
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:py-10">
        <SearchHero
          address={address}
          addressError={addressError}
          isGeocoding={isGeocoding}
          isSuggesting={isSuggesting}
          resolvedAddress={resolvedAddress}
          loadingResults={isLoading || isValidating}
          suggestions={suggestions}
          suggestionsOpen={suggestionsOpen}
          onAddressChange={handleAddressChange}
          onSearchAddress={searchAddress}
          onSelectSuggestion={selectSuggestion}
          onSuggestionsOpenChange={setSuggestionsOpen}
          demoMode={demoMode}
        />

        {!hasLocation ? <EmptyState /> : null}

        {hasLocation ? (
          <section className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-start">
            <PointResults
              points={data?.items ?? []}
              alert={data?.alerts?.[0]}
              error={error}
              loading={isLoading}
              returnParams={returnParams}
              selectedId={selectedPoint?.id ?? null}
              radiusM={filters.radiusM}
              demoMode={demoMode}
              onSelect={setSelectedId}
            />

            <aside className="lg:sticky lg:top-5">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-black">Mapa</h2>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-semibold text-[#5f5f5b]">
                    promień {filters.radiusM / 1000} km
                  </span>
                  <button
                    onClick={() => setFilters(f => ({ ...f, radiusM: Math.max(500, f.radiusM - 500) }))}
                    className="flex h-6 w-6 items-center justify-center rounded-md bg-black/5 text-xs font-black text-[#5f5f5b] transition-colors hover:bg-black/10"
                    title="Zmniejsz promień"
                  >
                    -
                  </button>
                  <button
                    onClick={() => setFilters(f => ({ ...f, radiusM: Math.min(10000, f.radiusM + 500) }))}
                    className="flex h-6 w-6 items-center justify-center rounded-md bg-black/5 text-xs font-black text-[#5f5f5b] transition-colors hover:bg-black/10"
                    title="Zwiększ promień"
                  >
                    +
                  </button>
                </div>
              </div>
              <MapShell
                points={data?.items ?? []}
                selectedPoint={selectedPoint}
                center={[filters.lat, filters.lng]}
                onSelectPoint={(point) => setSelectedId(point.id)}
              />
            </aside>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function SearchHero({
  address,
  addressError,
  isGeocoding,
  isSuggesting,
  loadingResults,
  resolvedAddress,
  suggestions,
  suggestionsOpen,
  onAddressChange,
  onSearchAddress,
  onSelectSuggestion,
  onSuggestionsOpenChange,
  demoMode,
}: {
  address: string;
  addressError: string | null;
  isGeocoding: boolean;
  isSuggesting: boolean;
  loadingResults: boolean;
  resolvedAddress: string | null;
  suggestions: GeocodeSuggestion[];
  suggestionsOpen: boolean;
  onAddressChange: (value: string) => void;
  onSearchAddress: () => void;
  onSelectSuggestion: (suggestion: GeocodeSuggestion) => void;
  onSuggestionsOpenChange: (open: boolean) => void;
  demoMode: boolean;
}) {
  return (
    <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7 lg:p-9">
      <div className="max-w-3xl">
        <p className="text-sm font-black uppercase text-[#5f5f5b]">Paczkomaty w pobliżu</p>
        <h1 className="mt-2 text-3xl font-black tracking-normal text-[#1d1d1b] sm:text-5xl">
          Znajdź najlepszy Paczkomat
        </h1>
      </div>

      <form
        className="mt-7 grid gap-3 rounded-lg bg-[#ffd200] p-3 sm:grid-cols-[minmax(0,1fr)_150px]"
        onSubmit={(event) => {
          event.preventDefault();
          onSearchAddress();
        }}
      >
        <div className="relative min-w-0">
          <label className="sr-only" htmlFor="address-search">
            Adres
          </label>
          <MapPin className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#5f5f5b]" />
          <input
            id="address-search"
            value={address}
            onChange={(event) => onAddressChange(event.target.value)}
            onFocus={() => {
              if (suggestions.length > 0) {
                onSuggestionsOpenChange(true);
              }
            }}
            onBlur={() => {
              window.setTimeout(() => onSuggestionsOpenChange(false), 120);
            }}
            placeholder="Wpisz adres, np. Długa 1, Gdańsk"
            className="h-14 w-full rounded-md border-2 border-transparent bg-white pl-12 pr-12 text-base font-semibold text-[#1d1d1b] outline-none placeholder:text-[#777770] focus:border-[#1d1d1b]"
            autoComplete="street-address"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={suggestionsOpen}
            aria-controls="address-suggestions"
          />
          {isSuggesting ? (
            <Loader2 className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 animate-spin text-[#5f5f5b]" />
          ) : null}

          {suggestionsOpen ? (
            <div
              id="address-suggestions"
              role="listbox"
              className="absolute left-0 right-0 top-[calc(100%+8px)] z-[1200] overflow-hidden rounded-lg border border-black/10 bg-white shadow-xl"
            >
              <div className="border-b border-black/10 px-4 py-2 text-xs font-black uppercase text-[#5f5f5b]">
                Podpowiedzi adresów
              </div>
              <div className="max-h-72 overflow-y-auto">
                {suggestions.map((suggestion) => (
                  <button
                    key={`${suggestion.display_name}-${suggestion.coordinates.lat}-${suggestion.coordinates.lng}`}
                    type="button"
                    role="option"
                    aria-selected="false"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => onSelectSuggestion(suggestion)}
                    className="flex w-full items-start gap-3 border-b border-black/5 px-4 py-3 text-left transition hover:bg-[#fff6bf] focus:bg-[#fff6bf] focus:outline-none"
                  >
                    <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#1d1d1b]" />
                    <span className="text-sm font-bold leading-5 text-[#1d1d1b]">
                      {suggestion.display_name}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
        <button
          type="submit"
          className="inline-flex h-14 items-center justify-center gap-2 rounded-md bg-[#1d1d1b] px-5 text-base font-black text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isGeocoding}
        >
          {isGeocoding ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
          Szukaj
        </button>
      </form>

      <div className="mt-3 min-h-6">
        {addressError ? (
          <p className="text-sm font-semibold text-red-700">{addressError}</p>
        ) : demoMode ? (
          <p className="line-clamp-1 text-sm font-bold text-[#1d1d1b]">
            Tryb demo jest włączony. Wyniki mogą zawierać lokalne dane przykładowe.
          </p>
        ) : resolvedAddress ? (
          <p className="line-clamp-1 text-sm font-medium text-[#5f5f5b]">
            Wyniki dla: {resolvedAddress}
            {loadingResults ? "..." : ""}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function EmptyState() {
  return (
    <section className="mt-8 rounded-xl border border-dashed border-black/20 bg-white p-8 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#ffd200]">
        <Search className="h-7 w-7 text-[#1d1d1b]" />
      </div>
      <h2 className="mt-4 text-xl font-black">Wpisz adres i sprawdź najbliższe punkty</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#5f5f5b]">
        Lista i mapa pojawią się dopiero po wyszukaniu lokalizacji.
      </p>
    </section>
  );
}

function PointResults({
  points,
  alert,
  error,
  loading,
  returnParams,
  selectedId,
  radiusM,
  demoMode,
  onSelect,
}: {
  points: PointSummary[];
  alert: PointSearchResponse["alerts"][number] | undefined;
  error: Error | undefined;
  loading: boolean;
  returnParams: URLSearchParams;
  selectedId: string | null;
  radiusM: number;
  demoMode: boolean;
  onSelect: (id: string) => void;
}) {
  if (error) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-800">
        <div className="flex items-center gap-2 font-black">
          <AlertTriangle className="h-5 w-5" />
          Nie udało się pobrać Paczkomatów
        </div>
        <p className="mt-2 text-sm">{error.message}</p>
      </section>
    );
  }

  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-black">Najlepsze Paczkomaty w pobliżu</h2>
          <p className="mt-1 text-sm font-medium text-[#5f5f5b]">
            {loading && points.length === 0 ? "Szukam punktów..." : `${points.length} wyników`}
          </p>
        </div>
      </div>

      {alert ? (
        <div className="mb-3 rounded-xl border border-[#ffd200] bg-[#fff6bf] p-4 text-sm font-semibold leading-6 text-[#1d1d1b]">
          <p className="font-black">{alert.title}</p>
          <p className="mt-1">{alert.message}</p>
        </div>
      ) : null}

      {demoMode ? (
        <div className="mb-3 rounded-xl border border-black/10 bg-white p-4 text-sm font-semibold leading-6 text-[#5f5f5b]">
          Tryb demo: obok realnych wyników mogą pojawić się przykładowe Paczkomaty z lokalnego seeda.
        </div>
      ) : null}

      <div className="grid gap-3">
        {loading && points.length === 0
          ? Array.from({ length: 5 }).map((_, index) => (
              <div
                key={index}
                className="h-28 animate-pulse rounded-xl border border-black/10 bg-white"
              />
            ))
          : null}

        {!loading && points.length === 0 ? (
          <div className="rounded-xl border border-black/10 bg-white p-6 text-sm font-medium text-[#5f5f5b]">
            Nie znaleziono Paczkomatów w promieniu {radiusM / 1000} km.
          </div>
        ) : null}

        {points.map((point, index) => (
          <PointCard
            key={point.id}
            point={point}
            rank={index + 1}
            href={pointHref(point, returnParams)}
            selected={selectedId === point.id}
            onSelect={() => onSelect(point.id)}
          />
        ))}
      </div>
    </section>
  );
}

function PointCard({
  point,
  rank,
  href,
  selected,
  onSelect,
}: {
  point: PointSummary;
  rank: number;
  href: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <Link
      href={href}
      onMouseEnter={onSelect}
      onFocus={onSelect}
      className={cn(
        "grid gap-4 rounded-xl border bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-[#1d1d1b] hover:shadow-md sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center",
        selected ? "border-[#ffd200] ring-2 ring-[#ffd200]/70" : "border-black/10",
      )}
    >
      <div className="flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1d1d1b] font-mono text-sm font-black text-white">
          {rank}
        </span>
        <ScoreBadge score={point.score} grade={point.grade} compact />
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-black text-[#1d1d1b]">{point.name}</h3>
          <span
            className={cn(
              "rounded-full border px-2.5 py-1 text-xs font-black",
              statusClass(point.status),
            )}
          >
            {statusLabel(point.status)}
          </span>
          {point.risk ? (
            <span
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-black",
                riskClass(point.risk.level),
              )}
            >
              {riskLabel(point.risk.level)}
            </span>
          ) : null}
        </div>
        <p className="mt-1 truncate text-base font-bold text-[#3c3c3c]">{shortAddress(point)}</p>
        <p className="mt-1 text-sm font-medium text-[#777770]">
          {formatDistance(point.distance_m)} od adresu
        </p>
      </div>

      <div className="flex items-center justify-between gap-3 sm:justify-end">
        <span className="text-sm font-black text-[#1d1d1b]">Szczegóły</span>
        <ChevronRight className="h-5 w-5 text-[#1d1d1b]" />
      </div>
    </Link>
  );
}
