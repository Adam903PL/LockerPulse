"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  ImagePlus,
  MapPin,
  Navigation,
  ShieldCheck,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import useSWR from "swr";
import {
  buildPointAlternativesUrl,
  buildPointHistoryUrl,
  buildPointUrl,
  createUserReport,
  fetchPointAlternatives,
  fetchPointDetails,
  fetchPointHistory,
} from "@/lib/api";
import {
  formatDistance,
  formatFunctionName,
  riskClass,
  riskLabel,
  statusClass,
  statusLabel,
} from "@/lib/point-display";
import { cn } from "@/lib/utils";
import type {
  PointAlternativesResponse,
  PointHistoryResponse,
  PointSummary,
  ReportReason,
  ReliabilitySummary,
  UserReportCreate,
  UserReportPhoto,
  UserReportResponse,
} from "@/types/points";
import { MapShell } from "./map-shell";
import { ScoreBadge } from "./score-badge";

type PointDetailPageProps = {
  country: string;
  name: string;
  returnQuery?: string;
  returnLat?: string;
  returnLng?: string;
  returnRadiusM?: number;
};

const MAX_REPORT_PHOTOS = 3;
const MAX_REPORT_PHOTO_BYTES = 1_500_000;
const ALLOWED_REPORT_PHOTO_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

type ReportPhotoDraft = UserReportPhoto & {
  id: string;
};

export function PointDetailPage({
  country,
  name,
  returnQuery,
  returnLat,
  returnLng,
  returnRadiusM = 3000,
}: PointDetailPageProps) {
  const { data, error, isLoading, mutate: mutatePoint } = useSWR(
    buildPointUrl(country, name, { lat: returnLat, lng: returnLng, radiusM: returnRadiusM }),
    fetchPointDetails,
    { revalidateOnFocus: false },
  );
  const {
    data: history,
    error: historyError,
    isLoading: historyLoading,
  } = useSWR(buildPointHistoryUrl(country, name, 7), fetchPointHistory, {
    revalidateOnFocus: false,
  });
  const alternativesUrl =
    returnLat && returnLng
      ? buildPointAlternativesUrl(country, name, {
          lat: returnLat,
          lng: returnLng,
          radiusM: returnRadiusM,
          limit: 3,
        })
      : null;
  const {
    data: alternatives,
    error: alternativesError,
    isLoading: alternativesLoading,
    mutate: mutateAlternatives,
  } = useSWR(alternativesUrl, fetchPointAlternatives, {
    revalidateOnFocus: false,
  });
  const backHref = buildBackHref(returnQuery, returnLat, returnLng, returnRadiusM);

  async function submitReport(payload: UserReportCreate): Promise<UserReportResponse> {
    const result = await createUserReport(country, name, payload);
    await Promise.all([mutatePoint(), mutateAlternatives()]);
    return result;
  }

  return (
    <main className="min-h-screen bg-[#f4f4f2] text-[#1d1d1b]">
      <header className="border-b border-black/10 bg-white">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/app" className="flex items-center gap-3" aria-label="LockerPulse app">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#ffd200] font-black text-[#1d1d1b]">
              LP
            </span>
            <span className="text-lg font-black">LockerPulse</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href={backHref}
              className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-black hover:bg-[#ffd200]"
            >
              <ArrowLeft className="h-4 w-4" />
              Wróć
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:py-10">
        {isLoading ? <DetailLoading /> : null}
        {error ? <DetailError message={error.message} /> : null}
        {data ? (
          <DetailContent
            point={data}
            history={history}
            historyLoading={historyLoading}
            historyError={historyError}
            alternatives={alternatives}
            alternativesLoading={alternativesLoading}
            alternativesError={alternativesError}
            returnQuery={returnQuery}
            returnLat={returnLat}
            returnLng={returnLng}
            returnRadiusM={returnRadiusM}
            onSubmitReport={submitReport}
          />
        ) : null}
      </div>
    </main>
  );
}

function DetailContent({
  point,
  history,
  historyLoading,
  historyError,
  alternatives,
  alternativesLoading,
  alternativesError,
  returnQuery,
  returnLat,
  returnLng,
  returnRadiusM,
  onSubmitReport,
}: {
  point: PointSummary;
  history: PointHistoryResponse | undefined;
  historyLoading: boolean;
  historyError: Error | undefined;
  alternatives: PointAlternativesResponse | undefined;
  alternativesLoading: boolean;
  alternativesError: Error | undefined;
  returnQuery?: string;
  returnLat?: string;
  returnLng?: string;
  returnRadiusM?: number;
  onSubmitReport: (payload: UserReportCreate) => Promise<UserReportResponse>;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-start">
      <section className="grid gap-5">
        <div className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-black uppercase text-[#5f5f5b]">Paczkomat</p>
              <h1 className="mt-1 text-4xl font-black tracking-normal">{point.name}</h1>
              <p className="mt-3 flex items-start gap-2 text-base font-bold text-[#3c3c3c]">
                <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-[#5f5f5b]" />
                <span>{point.address ?? "Adres niedostępny"}</span>
              </p>
            </div>
            <ScoreBadge score={point.score} grade={point.grade} />
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <DetailMetric label="Status" value={statusLabel(point.status)} tone={statusClass(point.status)} />
            <DetailMetric label="Odległość" value={formatDistance(point.distance_m)} />
            <DetailMetric label="Dostępność" value={point.location_247 ? "24/7" : "sprawdź godziny"} />
          </div>
        </div>

        <AdviceSection
          point={point}
          alternatives={alternatives}
          loading={alternativesLoading}
          error={alternativesError}
          hasLocationContext={Boolean(returnLat && returnLng)}
          returnQuery={returnQuery}
          returnLat={returnLat}
          returnLng={returnLng}
          returnRadiusM={returnRadiusM}
          onSubmitReport={onSubmitReport}
        />

        <ReliabilitySection
          pointReliability={point.reliability}
          history={history}
          loading={historyLoading}
          error={historyError}
        />

        <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
          <h2 className="text-2xl font-black">Dlaczego taka ocena?</h2>
          <div className="mt-5 grid gap-3">
            {[...point.reasons, ...(point.history_reasons ?? [])].map((reason) => (
              <div key={reason} className="flex gap-3 rounded-lg border border-black/10 bg-[#f8f8f6] p-4">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
                <p className="text-sm font-semibold leading-6 text-[#3c3c3c]">{reason}</p>
              </div>
            ))}
            {point.problem_reasons.map((reason) => (
              <div key={reason} className="flex gap-3 rounded-lg border border-[#ffd200] bg-[#fffbea] p-4">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[#1d1d1b]" />
                <p className="text-sm font-semibold leading-6 text-[#3c3c3c]">{reason}</p>
              </div>
            ))}
          </div>

          {[...point.warnings, ...(point.history_warnings ?? [])].length > 0 ? (
            <div className="mt-5 rounded-lg border border-amber-300 bg-amber-50 p-4">
              <h3 className="flex items-center gap-2 text-base font-black text-amber-950">
                <AlertTriangle className="h-5 w-5" />
                Uwaga na dane
              </h3>
              <ul className="mt-3 grid gap-2 text-sm font-semibold leading-6 text-amber-950">
                {[...point.warnings, ...(point.history_warnings ?? [])].map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
          <h2 className="text-2xl font-black">Dostępne akcje</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {point.functions.length > 0 ? (
              point.functions.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-black/10 bg-[#ffd200] px-3 py-1.5 text-xs font-black text-[#1d1d1b]"
                >
                  {formatFunctionName(item)}
                </span>
              ))
            ) : (
              <p className="text-sm font-semibold text-[#5f5f5b]">Brak danych o akcjach.</p>
            )}
          </div>
        </section>
      </section>

      <aside className="grid gap-5 lg:sticky lg:top-5">
        <PointImage point={point} />
        <MapShell
          points={[point]}
          selectedPoint={point}
          center={[point.coordinates.lat, point.coordinates.lng]}
          onSelectPoint={() => undefined}
        />
      </aside>
    </div>
  );
}

function AdviceSection({
  point,
  alternatives,
  loading,
  error,
  hasLocationContext,
  returnQuery,
  returnLat,
  returnLng,
  returnRadiusM,
  onSubmitReport,
}: {
  point: PointSummary;
  alternatives: PointAlternativesResponse | undefined;
  loading: boolean;
  error: Error | undefined;
  hasLocationContext: boolean;
  returnQuery?: string;
  returnLat?: string;
  returnLng?: string;
  returnRadiusM?: number;
  onSubmitReport: (payload: UserReportCreate) => Promise<UserReportResponse>;
}) {
  const risk = alternatives?.risk ?? point.risk;
  const best = alternatives?.alternatives[0];
  const reportSummary = alternatives?.point.report_summary ?? point.report_summary;
  const isProblem = risk?.level === "critical" || risk?.level === "risky";
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);

  async function submitReport(payload: UserReportCreate) {
    setReportSuccess(null);
    await onSubmitReport(payload);
    setIsReportOpen(false);
    setReportSuccess("Zgłoszenie zapisane. Ocena problemu pojawi się za chwilę.");
  }

  return (
    <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-black">Czy warto tu iść?</h2>
          <p className="mt-2 text-sm font-semibold leading-6 text-[#5f5f5b]">
            {risk?.message ?? "Sprawdzamy status, score i historię tego punktu."}
          </p>
        </div>
        {risk ? (
          <span className={cn("rounded-full border px-3 py-1.5 text-xs font-black", riskClass(risk.level))}>
            {riskLabel(risk.level)}
          </span>
        ) : null}
      </div>

      <div className="mt-5 rounded-lg border border-black/10 bg-[#f8f8f6] p-4">
        <p className="text-xs font-black uppercase text-[#5f5f5b]">Zgłoszenia użytkowników</p>
        <p className="mt-1 text-base font-black">{reportSummary?.label ?? "Brak zgłoszeń"}</p>
        <p className="mt-1 text-sm font-semibold leading-6 text-[#5f5f5b]">
          {reportSummary?.message ?? "Nie ma świeżych zgłoszeń problemu dla tego punktu."}
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <DetailMetric label="Problem score 24h" value={`${reportSummary?.problem_score_24h ?? 0}/100`} />
          <DetailMetric label="Kara zgłoszeń" value={`-${reportSummary?.community_penalty ?? 0} pkt`} />
          <DetailMetric label="Źródło oceny" value={analysisSourceText(reportSummary)} />
        </div>
        {(reportSummary?.analysis_count ?? 0) > 0 ? (
          <p className="mt-3 text-xs font-semibold leading-5 text-[#777770]">
            Ocena zgłoszeń jest zapisywana raz po dodaniu raportu. Wynik wpływa na score tylko przez świeże analizy z
            ostatnich 24h. {analysisStatusText(reportSummary)}.
          </p>
        ) : null}
      </div>

      {isProblem ? (
        <div className="mt-5 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm font-semibold leading-6 text-amber-950">
          Ten punkt może być problematyczny dzisiaj. Jeżeli możesz, wybierz lepszą alternatywę w pobliżu.
        </div>
      ) : null}

      <div className="mt-5">
        <button
          type="button"
          onClick={() => {
            setIsReportOpen(true);
            setReportSuccess(null);
          }}
          className="inline-flex h-11 items-center justify-center rounded-md bg-[#1d1d1b] px-4 text-sm font-black text-white transition hover:bg-black"
        >
          Zgłoś problem
        </button>
        {reportSuccess ? (
          <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
            {reportSuccess}
          </p>
        ) : null}
      </div>

      {isReportOpen ? (
        <ReportProblemModal
          returnLat={returnLat}
          returnLng={returnLng}
          onClose={() => setIsReportOpen(false)}
          onSubmit={submitReport}
        />
      ) : null}

      {!hasLocationContext ? (
        <p className="mt-5 rounded-lg border border-black/10 bg-[#f8f8f6] p-4 text-sm font-semibold text-[#5f5f5b]">
          Alternatywy pojawią się, gdy wejdziesz w szczegóły z wyników wyszukiwania adresu.
        </p>
      ) : null}

      {loading ? (
        <div className="mt-5 h-24 animate-pulse rounded-lg bg-[#f8f8f6]" />
      ) : null}

      {error ? (
        <p className="mt-5 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm font-semibold text-amber-950">
          Nie udało się pobrać alternatyw: {error.message}
        </p>
      ) : null}

      {best ? (
        <div className="mt-5 rounded-lg border border-[#ffd200] bg-[#fffbea] p-4">
          <div className="min-w-0">
            <p className="text-xs font-black uppercase text-[#5f5f5b]">
              {alternatives?.plan_b_message ? "Plan B" : "Lepsza alternatywa w pobliżu"}
            </p>
            <h3 className="mt-1 text-xl font-black">{best.name}</h3>
            <p className="mt-1 truncate text-sm font-bold text-[#3c3c3c]">{best.address ?? "Adres niedostępny"}</p>
            <p className="mt-1 text-sm font-semibold text-[#777770]">{formatDistance(best.distance_m)} od adresu</p>
            {alternatives?.plan_b_message ? (
              <p className="mt-2 text-sm font-semibold leading-6 text-[#5f5f5b]">{alternatives.plan_b_message}</p>
            ) : null}
          </div>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
            <ScoreBadge score={best.score} grade={best.grade} compact />
            <Link
              href={buildPointContextHref(best, returnQuery, returnLat, returnLng, returnRadiusM)}
              className="inline-flex h-10 items-center justify-center rounded-md border border-black/10 bg-white px-3 text-sm font-black hover:bg-[#ffd200]"
            >
              Szczegóły
            </Link>
            <a
              href={googleMapsHref(best)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-[#1d1d1b] px-3 text-sm font-black text-white hover:bg-black"
            >
              <Navigation className="h-4 w-4" />
              Prowadź w Google Maps
            </a>
          </div>
        </div>
      ) : alternatives && hasLocationContext ? (
        <p className="mt-5 rounded-lg border border-black/10 bg-[#f8f8f6] p-4 text-sm font-semibold text-[#5f5f5b]">
          {alternatives.message}
        </p>
      ) : null}
    </section>
  );
}

function ReportProblemModal({
  returnLat,
  returnLng,
  onClose,
  onSubmit,
}: {
  returnLat?: string;
  returnLng?: string;
  onClose: () => void;
  onSubmit: (payload: UserReportCreate) => Promise<void>;
}) {
  const [reportReason, setReportReason] = useState<ReportReason>("not_working");
  const [reportComment, setReportComment] = useState("");
  const [photos, setPhotos] = useState<ReportPhotoDraft[]>([]);
  const [reportError, setReportError] = useState<string | null>(null);
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);

  async function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const comment = reportComment.trim();
    if (comment.length < 10) {
      setReportError("Komentarz musi mieć co najmniej 10 znaków.");
      return;
    }

    setIsSubmittingReport(true);
    setReportError(null);
    try {
      await onSubmit({
        reason: reportReason,
        comment,
        photos: photos.map((photo) => ({
          file_name: photo.file_name,
          content_type: photo.content_type,
          size_bytes: photo.size_bytes,
          data_url: photo.data_url,
        })),
        lat: returnLat ? Number(returnLat) : undefined,
        lng: returnLng ? Number(returnLng) : undefined,
      });
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "Nie udało się wysłać zgłoszenia.");
    } finally {
      setIsSubmittingReport(false);
    }
  }

  async function addPhotos(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.currentTarget.files ?? []);
    event.currentTarget.value = "";
    if (files.length === 0) {
      return;
    }

    if (photos.length + files.length > MAX_REPORT_PHOTOS) {
      setReportError(`Możesz dodać maksymalnie ${MAX_REPORT_PHOTOS} zdjęcia.`);
      return;
    }

    try {
      const nextPhotos = await Promise.all(files.map(readReportPhoto));
      setPhotos((current) => [...current, ...nextPhotos]);
      setReportError(null);
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "Nie udało się dodać zdjęcia.");
    }
  }

  function removePhoto(id: string) {
    setPhotos((current) => current.filter((photo) => photo.id !== id));
  }

  return (
    <div className="fixed inset-0 z-[1000] flex items-end justify-center bg-black/55 px-4 py-4 sm:items-center">
      <button
        type="button"
        aria-label="Zamknij okno zgłoszenia"
        onClick={onClose}
        className="absolute inset-0 cursor-default"
      />
      <form
        onSubmit={submitReport}
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-dialog-title"
        className="relative max-h-[92vh] w-full max-w-xl overflow-y-auto rounded-xl border border-black/10 bg-white p-5 shadow-2xl sm:p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase text-[#5f5f5b]">Zgłoszenie użytkownika</p>
            <h3 id="report-dialog-title" className="mt-1 text-2xl font-black">
              Zgłoś problem z Paczkomatem
            </h3>
            <p className="mt-2 text-sm font-semibold leading-6 text-[#5f5f5b]">
              Opisz, co się stało. Zdjęcia są opcjonalne, ale pomagają lepiej zrozumieć problem.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-black/10 bg-white text-[#1d1d1b] hover:bg-[#ffd200]"
            aria-label="Zamknij"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-5 grid gap-4">
          <label className="grid gap-2 text-sm font-black">
            Powód
            <select
              value={reportReason}
              onChange={(event) => setReportReason(event.target.value as ReportReason)}
              className="h-12 rounded-md border border-black/10 bg-white px-3 text-sm font-semibold outline-none focus:border-[#1d1d1b]"
            >
              <option value="not_working">Paczkomat nie działa</option>
              <option value="full">Brak miejsca</option>
              <option value="screen_problem">Problem z ekranem</option>
              <option value="access_problem">Problem z dostępem</option>
              <option value="other">Inne</option>
            </select>
          </label>

          <label className="grid gap-2 text-sm font-black">
            Komentarz
            <textarea
              value={reportComment}
              onChange={(event) => setReportComment(event.target.value)}
              minLength={10}
              maxLength={500}
              required
              rows={5}
              placeholder="Opisz krótko co się stało, np. ekran nie reaguje albo nie można otworzyć skrytki."
              className="resize-none rounded-md border border-black/10 bg-white p-3 text-sm font-semibold leading-6 outline-none focus:border-[#1d1d1b]"
            />
            <span className="text-xs font-semibold text-[#777770]">{reportComment.length}/500 znaków</span>
          </label>

          <div className="grid gap-2">
            <p className="text-sm font-black">Zdjęcia</p>
            <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-black/15 bg-[#f8f8f6] p-5 text-center transition hover:border-[#1d1d1b] hover:bg-[#fffbea]">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={addPhotos}
                className="sr-only"
              />
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-md bg-[#ffd200]">
                <Upload className="h-5 w-5" />
              </span>
              <span className="text-sm font-black">Dodaj zdjęcia</span>
              <span className="text-xs font-semibold leading-5 text-[#777770]">
                JPG, PNG lub WEBP. Maksymalnie {MAX_REPORT_PHOTOS} zdjęcia, do {formatFileSize(MAX_REPORT_PHOTO_BYTES)} każde.
              </span>
            </label>

            {photos.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-3">
                {photos.map((photo) => (
                  <div key={photo.id} className="rounded-lg border border-black/10 bg-white p-2">
                    <div
                      className="aspect-square rounded-md bg-cover bg-center"
                      style={{ backgroundImage: `url(${photo.data_url})` }}
                      aria-label={`Podgląd zdjęcia ${photo.file_name}`}
                    />
                    <div className="mt-2 min-w-0">
                      <p className="truncate text-xs font-black">{photo.file_name}</p>
                      <p className="text-xs font-semibold text-[#777770]">{formatFileSize(photo.size_bytes)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removePhoto(photo.id)}
                      className="mt-2 inline-flex h-8 w-full items-center justify-center gap-2 rounded-md border border-black/10 bg-white text-xs font-black hover:bg-red-50 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                      Usuń
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="flex items-center gap-2 text-xs font-semibold text-[#777770]">
                <ImagePlus className="h-4 w-4" />
                Nie dodano zdjęć.
              </p>
            )}
          </div>
        </div>

        {reportError ? <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{reportError}</p> : null}

        <div className="mt-5 flex flex-col gap-2 sm:flex-row">
          <button
            type="submit"
            disabled={isSubmittingReport}
            className="inline-flex h-12 items-center justify-center rounded-md bg-[#ffd200] px-4 text-sm font-black text-[#1d1d1b] transition hover:bg-[#f0c400] disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmittingReport ? "Wysyłanie..." : "Wyślij zgłoszenie"}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmittingReport}
            className="inline-flex h-12 items-center justify-center rounded-md border border-black/10 bg-white px-4 text-sm font-black text-[#1d1d1b] transition hover:bg-[#f8f8f6] disabled:cursor-not-allowed disabled:opacity-70"
          >
            Anuluj
          </button>
        </div>
      </form>
    </div>
  );
}

function ReliabilitySection({
  pointReliability,
  history,
  loading,
  error,
}: {
  pointReliability: ReliabilitySummary | null | undefined;
  history: PointHistoryResponse | undefined;
  loading: boolean;
  error: Error | undefined;
}) {
  const reliability = history?.reliability ?? pointReliability;

  if (loading && !history) {
    return (
      <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
        <div className="h-28 animate-pulse rounded-lg bg-[#f8f8f6]" />
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-xl border border-amber-300 bg-amber-50 p-5 text-amber-950 shadow-sm sm:p-7">
        <h2 className="text-2xl font-black">Niezawodność</h2>
        <p className="mt-2 text-sm font-semibold">Nie udało się pobrać historii: {error.message}</p>
      </section>
    );
  }

  if (!reliability || reliability.snapshot_count === 0) {
    return (
      <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-[#5f5f5b]" />
          <h2 className="text-2xl font-black">Niezawodność</h2>
        </div>
        <p className="mt-3 text-sm font-semibold leading-6 text-[#5f5f5b]">
          Historia pojawi się po kilku uruchomieniach collectora.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-6 w-6 text-emerald-700" />
            <h2 className="text-2xl font-black">Niezawodność</h2>
          </div>
          <p className="mt-2 text-sm font-semibold text-[#5f5f5b]">
            {reliabilityLabel(reliability)} przez ostatnie {history?.window_days ?? 7} dni
          </p>
        </div>
        <span className={cn("rounded-full border px-3 py-1.5 text-xs font-black", reliabilityClass(reliability.label))}>
          {reliability.label}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <DetailMetric label="Pomiary" value={String(reliability.snapshot_count)} />
        <DetailMetric label="Uptime" value={formatUptime(reliability.uptime_ratio)} />
        <DetailMetric label="Zmiany" value={String(reliability.status_changes)} />
      </div>

      {history?.timeline.length ? (
        <div className="mt-5">
          <h3 className="text-sm font-black uppercase text-[#5f5f5b]">Ostatnie pomiary</h3>
          <div className="mt-3 grid gap-2">
            {history.timeline.slice(0, 6).map((item) => (
              <div
                key={`${item.collected_at}-${item.status}-${item.score}`}
                className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-black/10 bg-[#f8f8f6] p-3"
              >
                <Clock3 className="h-4 w-4 text-[#5f5f5b]" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-black">{statusLabel(item.status)}</p>
                  <p className="text-xs font-semibold text-[#777770]">{formatDateTime(item.collected_at)}</p>
                </div>
                <span className="rounded-md bg-[#ffd200] px-2 py-1 font-mono text-xs font-black">
                  {item.score}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {history?.events.length ? (
        <div className="mt-5 rounded-lg border border-amber-300 bg-amber-50 p-4">
          <h3 className="text-sm font-black uppercase text-amber-950">Ostatnie zmiany</h3>
          <ul className="mt-3 grid gap-2 text-sm font-semibold text-amber-950">
            {history.events.slice(0, 4).map((event) => (
              <li key={`${event.detected_at}-${event.event_type}`}>
                {formatDateTime(event.detected_at)}: {statusLabel(event.from_status)} → {statusLabel(event.to_status)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function PointImage({ point }: { point: PointSummary }) {
  if (!point.image_url) {
    return (
      <div className="flex aspect-[4/3] items-center justify-center rounded-xl border border-black/10 bg-white p-6 text-center text-sm font-semibold text-[#5f5f5b] shadow-sm">
        Brak publicznego zdjęcia tego punktu.
      </div>
    );
  }

  return (
    <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-black/10 bg-white shadow-sm">
      <Image
        src={point.image_url}
        alt={`Paczkomat ${point.name}`}
        fill
        sizes="(max-width: 1024px) 100vw, 420px"
        className="object-cover"
      />
    </div>
  );
}

function DetailMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-black/10 bg-[#f8f8f6] p-4", tone)}>
      <p className="text-xs font-black uppercase opacity-70">{label}</p>
      <p className="mt-1 text-sm font-black">{value}</p>
    </div>
  );
}

function DetailLoading() {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
      <div className="grid gap-5">
        <div className="h-52 animate-pulse rounded-xl border border-black/10 bg-white" />
        <div className="h-72 animate-pulse rounded-xl border border-black/10 bg-white" />
      </div>
      <div className="h-80 animate-pulse rounded-xl border border-black/10 bg-white" />
    </div>
  );
}

function DetailError({ message }: { message: string }) {
  return (
    <section className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-800">
      <div className="flex items-center gap-2 font-black">
        <AlertTriangle className="h-5 w-5" />
        Nie udało się pobrać szczegółów
      </div>
      <p className="mt-2 text-sm">{message}</p>
    </section>
  );
}

function buildBackHref(query?: string, lat?: string, lng?: string, radiusM?: number) {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  if (lat && lng) {
    params.set("lat", lat);
    params.set("lng", lng);
  }
  if (radiusM) {
    params.set("radius_m", String(radiusM));
  }
  const suffix = params.toString();
  return suffix ? `/app?${suffix}` : "/app";
}

function buildPointContextHref(
  point: PointSummary,
  query?: string,
  lat?: string,
  lng?: string,
  radiusM?: number,
) {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  if (lat && lng) {
    params.set("lat", lat);
    params.set("lng", lng);
  }
  if (radiusM) {
    params.set("radius_m", String(radiusM));
  }
  const suffix = params.toString();
  return `/points/${point.country}/${point.name}${suffix ? `?${suffix}` : ""}`;
}

function googleMapsHref(point: PointSummary) {
  const destination = `${point.coordinates.lat},${point.coordinates.lng}`;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;
}

function reliabilityLabel(reliability: ReliabilitySummary) {
  if (reliability.label === "stabilny") {
    return "Stabilny";
  }
  if (reliability.label === "raczej stabilny") {
    return "Raczej stabilny";
  }
  if (reliability.label === "problem") {
    return "Problem w historii";
  }
  if (reliability.label === "niestabilny") {
    return "Niestabilny";
  }
  return "Za mało danych";
}

function reliabilityClass(label: string) {
  if (label === "stabilny") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (label === "raczej stabilny") {
    return "border-[#ffd200] bg-[#fff4b8] text-[#1d1d1b]";
  }
  if (label === "problem" || label === "niestabilny") {
    return "border-red-200 bg-red-50 text-red-800";
  }
  return "border-zinc-200 bg-zinc-100 text-zinc-700";
}

function analysisStatusText(summary: PointSummary["report_summary"]) {
  if (!summary) {
    return "0";
  }
  if (summary.analysis_pending_count > 0) {
    return `${summary.analysis_count} gotowe, ${summary.analysis_pending_count} w toku`;
  }
  return `${summary.analysis_count} gotowe`;
}

function analysisSourceText(summary: PointSummary["report_summary"]) {
  if (!summary || summary.analysis_count + summary.analysis_pending_count === 0) {
    return "Brak";
  }
  if (summary.analysis_mode === "rules_fallback") {
    return "Fallback regułowy";
  }
  if (summary.analysis_provider === "rules") {
    return "Analiza regułowa";
  }
  if (summary.analysis_provider === "litellm") {
    return summary.analysis_model ? `Model: ${summary.analysis_model}` : "Model";
  }
  if (summary.analysis_pending_count > 0) {
    return "W toku";
  }
  return "Analiza";
}

function formatUptime(value: number | null) {
  if (value == null) {
    return "brak danych";
  }
  return `${Math.round(value * 100)}%`;
}

async function readReportPhoto(file: File): Promise<ReportPhotoDraft> {
  if (!ALLOWED_REPORT_PHOTO_TYPES.has(file.type)) {
    throw new Error("Dodaj zdjęcie w formacie JPG, PNG albo WEBP.");
  }
  if (file.size > MAX_REPORT_PHOTO_BYTES) {
    throw new Error(`Zdjęcie ${file.name} jest za duże. Limit to ${formatFileSize(MAX_REPORT_PHOTO_BYTES)}.`);
  }

  const dataUrl = await readFileAsDataUrl(file);
  return {
    id: typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${file.name}-${Date.now()}`,
    file_name: file.name.slice(0, 160),
    content_type: file.type,
    size_bytes: file.size,
    data_url: dataUrl,
  };
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("Nie udało się odczytać zdjęcia."));
      }
    };
    reader.onerror = () => reject(new Error("Nie udało się odczytać zdjęcia."));
    reader.readAsDataURL(file);
  });
}

function formatFileSize(value: number) {
  if (value < 1024 * 1024) {
    return `${Math.round(value / 1024)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
