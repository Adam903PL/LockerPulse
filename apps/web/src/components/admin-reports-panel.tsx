"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Shield, Trash2 } from "lucide-react";
import useSWR from "swr";
import {
  buildAdminReportsUrl,
  deleteAdminReport,
  fetchAdminReports,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AdminReportItem } from "@/types/points";

const REASON_LABELS: Record<string, string> = {
  not_working: "Nie działa",
  full: "Brak miejsca",
  screen_problem: "Ekran",
  access_problem: "Dostęp",
  other: "Inne",
};

export function AdminReportsPanel() {
  const [token, setToken] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return window.localStorage.getItem("lockerpulse-admin-token") ?? "";
  });
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reportsUrl = useMemo(() => buildAdminReportsUrl({ limit: 200 }), []);
  const { data, error, isLoading, mutate } = useSWR(
    [reportsUrl, token],
    fetchAdminReports,
    { revalidateOnFocus: false },
  );

  function saveToken(value: string) {
    setToken(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("lockerpulse-admin-token", value);
    }
  }

  async function removeReport(report: AdminReportItem) {
    const confirmed = window.confirm(`Usunąć zgłoszenie ${report.id}? Tej akcji nie da się cofnąć.`);
    if (!confirmed) {
      return;
    }
    setDeletingId(report.id);
    setNotice(null);
    try {
      await deleteAdminReport(report.id, token);
      await mutate();
      setNotice(`Usunięto zgłoszenie ${report.id}.`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Nie udało się usunąć zgłoszenia.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#f4f4f2] text-[#1d1d1b]">
      <header className="border-b border-black/10 bg-white">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3" aria-label="LockerPulse home">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#ffd200] font-black">
              LP
            </span>
            <span className="text-lg font-black">LockerPulse Admin</span>
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-black hover:bg-[#ffd200]"
          >
            <ArrowLeft className="h-4 w-4" />
            Wróć
          </Link>
        </div>
      </header>

      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:py-10">
        <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-black uppercase text-[#5f5f5b]">Panel administracyjny</p>
              <h1 className="mt-2 text-3xl font-black tracking-normal sm:text-5xl">
                Zgłoszenia użytkowników
              </h1>
              <p className="mt-3 max-w-2xl text-sm font-semibold leading-6 text-[#5f5f5b]">
                Tu podejrzysz zgłoszenia, status analizy AI i usuniesz błędne albo testowe wpisy.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <button
                type="button"
                onClick={() => mutate()}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-black/10 bg-white px-4 text-sm font-black hover:bg-[#ffd200]"
              >
                <RefreshCw className="h-4 w-4" />
                Odśwież
              </button>
            </div>
          </div>

          <div className="mt-5 rounded-lg border border-[#ffd200] bg-[#fffbea] p-4">
            <label className="grid gap-2 text-sm font-black">
              <span className="inline-flex items-center gap-2">
                <Shield className="h-4 w-4" />
                Admin token
              </span>
              <input
                value={token}
                onChange={(event) => saveToken(event.target.value)}
                placeholder="Zostaw puste lokalnie, jeśli ADMIN_TOKEN nie jest ustawiony"
                className="h-11 rounded-md border border-black/10 bg-white px-3 text-sm font-semibold outline-none focus:border-[#1d1d1b]"
              />
            </label>
          </div>
        </section>

        {notice ? (
          <div className="mt-4 rounded-xl border border-black/10 bg-white p-4 text-sm font-bold text-[#1d1d1b]">
            {notice}
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-bold text-red-800">
            {error.message}
          </div>
        ) : null}

        <section className="mt-5 grid gap-3">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-32 animate-pulse rounded-xl border border-black/10 bg-white" />
            ))
          ) : null}

          {!isLoading && data?.items.length === 0 ? (
            <div className="rounded-xl border border-black/10 bg-white p-6 text-sm font-semibold text-[#5f5f5b]">
              Brak zgłoszeń.
            </div>
          ) : null}

          {data?.items.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              deleting={deletingId === report.id}
              onDelete={() => removeReport(report)}
            />
          ))}
        </section>
      </div>
    </main>
  );
}

function ReportCard({
  report,
  deleting,
  onDelete,
}: {
  report: AdminReportItem;
  deleting: boolean;
  onDelete: () => void;
}) {
  return (
    <article className="rounded-xl border border-black/10 bg-white p-4 shadow-sm sm:p-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/points/${report.country}/${report.name}`} className="text-xl font-black hover:underline">
              {report.name}
            </Link>
            <span className="rounded-full border border-black/10 bg-[#ffd200] px-2.5 py-1 text-xs font-black">
              {REASON_LABELS[report.reason] ?? report.reason}
            </span>
            <span className={cn("rounded-full border px-2.5 py-1 text-xs font-black", statusClass(report.analysis_status))}>
              {analysisLabel(report.analysis_status, report.analysis)}
            </span>
          </div>

          <p className="mt-2 text-sm font-semibold text-[#5f5f5b]">
            {report.point_address ?? `${report.country}:${report.name}`} · {formatDateTime(report.created_at)} · zdjęcia: {report.photos_count}
          </p>
          <p className="mt-3 rounded-lg border border-black/10 bg-[#f8f8f6] p-3 text-sm font-semibold leading-6 text-[#3c3c3c]">
            {report.comment}
          </p>

          {report.analysis ? (
            <div className="mt-3 grid gap-2 sm:grid-cols-6">
              <Metric label="Severity" value={`${report.analysis.severity}/100`} />
              <Metric label="Confidence" value={`${Math.round(report.analysis.confidence * 100)}%`} />
              <Metric label="Penalty" value={`-${report.analysis.score_penalty}`} />
              <Metric label="Risk floor" value={report.analysis.recommended_risk_floor} />
              <Metric label="Provider" value={analysisProviderLabel(report.analysis)} />
              <Metric label="Mode" value={analysisModeLabel(report.analysis.analysis_mode)} />
            </div>
          ) : null}
          {report.analysis?.error ? (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs font-semibold leading-5 text-amber-900">
              {report.analysis.error}
            </p>
          ) : null}
        </div>

        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 text-sm font-black text-red-800 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Trash2 className="h-4 w-4" />
          {deleting ? "Usuwam..." : "Usuń"}
        </button>
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-black/10 bg-[#fffbea] p-3">
      <p className="text-xs font-black uppercase text-[#777770]">{label}</p>
      <p className="mt-1 text-sm font-black">{value}</p>
    </div>
  );
}

function analysisLabel(status: string | null, analysis?: AdminReportItem["analysis"]) {
  if (status === "ok") {
    if (analysis?.analysis_mode === "rules_fallback") {
      return "Fallback regułowy";
    }
    if (analysis?.provider === "rules") {
      return "Reguły";
    }
    if (analysis?.provider === "litellm") {
      return "LiteLLM";
    }
    return "OK";
  }
  if (status === "failed") {
    return "Błąd analizy";
  }
  if (status === "pending") {
    return "W toku";
  }
  return "Bez analizy";
}

function analysisProviderLabel(analysis: AdminReportItem["analysis"]) {
  if (!analysis) {
    return "Brak";
  }
  if (analysis.provider === "rules") {
    return "Reguły";
  }
  if (analysis.provider === "litellm") {
    return analysis.model_name || "LiteLLM";
  }
  return analysis.provider;
}

function analysisModeLabel(mode: string) {
  if (mode === "rules_fallback") {
    return "Fallback";
  }
  if (mode === "rules") {
    return "Reguły";
  }
  if (mode === "litellm") {
    return "Model";
  }
  return mode;
}

function statusClass(status: string | null) {
  if (status === "ok") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "failed") {
    return "border-red-200 bg-red-50 text-red-800";
  }
  if (status === "pending") {
    return "border-[#ffd200] bg-[#fff6bf] text-[#1d1d1b]";
  }
  return "border-zinc-200 bg-zinc-100 text-zinc-700";
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
