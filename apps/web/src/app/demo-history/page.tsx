import Link from "next/link";
import { ArrowLeft, ChevronRight, DatabaseZap } from "lucide-react";
import { DemoModeSwitch } from "@/components/demo-mode-switch";

type DemoCase = {
  name: string;
  address: string;
  lat: number;
  lng: number;
  label: string;
  tone: "good" | "ok" | "bad" | "neutral";
  description: string;
};

const DEMO_CASES: DemoCase[] = [
  {
    name: "SYZ01M",
    address: "Strzyżewice 108, 23-107 Strzyżewice",
    lat: 51.0808,
    lng: 22.4416,
    label: "Problem",
    tone: "bad",
    description: "Dużo awarii w tygodniu i aktualny status Disabled.",
  },
  {
    name: "SYZGOOD1",
    address: "Strzyżewice 118A, 23-107 Strzyżewice",
    lat: 51.084,
    lng: 22.447,
    label: "Alternatywa",
    tone: "good",
    description: "Stabilny punkt blisko SYZ01M, używany w demo alternatyw.",
  },
  {
    name: "SYZGOOD2",
    address: "Piotrowice 12, 23-107 Strzyżewice",
    lat: 51.096,
    lng: 22.425,
    label: "Alternatywa",
    tone: "good",
    description: "Drugi stabilny punkt w promieniu demo dla SYZ01M.",
  },
  {
    name: "WAWSTABLE1",
    address: "Marszałkowska 104/122, Warszawa",
    lat: 52.2319,
    lng: 21.0067,
    label: "Stabilny",
    tone: "good",
    description: "Dziesięć pomiarów bez żadnej zmiany statusu.",
  },
  {
    name: "GDARATHER1",
    address: "Długa 1, Gdańsk",
    lat: 54.3504,
    lng: 18.6534,
    label: "Raczej stabilny",
    tone: "ok",
    description: "Jeden krótki problem w środku tygodnia.",
  },
  {
    name: "LODFLIP1",
    address: "Piotrkowska 86, Łódź",
    lat: 51.7671,
    lng: 19.456,
    label: "Niestabilny",
    tone: "bad",
    description: "Status często przeskakuje między Operating i Disabled.",
  },
  {
    name: "POZDOWN1",
    address: "Półwiejska 42, Poznań",
    lat: 52.4021,
    lng: 16.9292,
    label: "Problem",
    tone: "bad",
    description: "Działał stabilnie, ale ostatnie pomiary są niedostępne.",
  },
  {
    name: "WROSHORT1",
    address: "Rynek 14, Wrocław",
    lat: 51.1094,
    lng: 17.0326,
    label: "Za mało danych",
    tone: "neutral",
    description: "Tylko jeden snapshot, więc panel pokazuje spokojny empty state.",
  },
  {
    name: "LUBAVAIL1",
    address: "Krakowskie Przedmieście 40, Lublin",
    lat: 51.2465,
    lng: 22.5674,
    label: "Stabilny",
    tone: "good",
    description: "Status działa, ale pole dostępności zmienia się w danych źródłowych.",
  },
  {
    name: "RZECREATED1",
    address: "3 Maja 2, Rzeszów",
    lat: 50.0381,
    lng: 22.0047,
    label: "Po uruchomieniu",
    tone: "ok",
    description: "Pierwsze pomiary Created, potem punkt przechodzi na Operating.",
  },
  {
    name: "BIALOW1",
    address: "Lipowa 12, Białystok",
    lat: 53.1325,
    lng: 23.1591,
    label: "Stabilny, niższy score",
    tone: "neutral",
    description: "Historia jest dobra, ale sam punkt ma mniej wygodne parametry.",
  },
  {
    name: "KATMAINT1",
    address: "Stawowa 13, Katowice",
    lat: 50.2604,
    lng: 19.0216,
    label: "Niestabilny",
    tone: "bad",
    description: "Dwie przerwy serwisowe w ostatnich siedmiu dniach.",
  },
];

export const metadata = {
  title: "Demo historii | LockerPulse",
};

type DemoHistoryPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function DemoHistoryPage({ searchParams }: DemoHistoryPageProps) {
  const params = await searchParams;
  const demoMode = parseDemo(first(params.demo));

  return (
    <main className="min-h-screen bg-[#f4f4f2] text-[#1d1d1b]">
      <header className="border-b border-black/10 bg-white">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3" aria-label="LockerPulse home">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#ffd200] font-black text-[#1d1d1b]">
              LP
            </span>
            <span className="text-lg font-black tracking-normal">LockerPulse</span>
          </Link>
          <div className="flex items-center gap-2">
            <DemoModeSwitch enabled={demoMode} />
            <Link
              href="/app"
              className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-black hover:bg-[#ffd200]"
            >
              <ArrowLeft className="h-4 w-4" />
              Wróć
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:py-10">
        {!demoMode ? (
          <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7 lg:p-9">
            <p className="text-sm font-black uppercase text-[#5f5f5b]">Tryb demo jest wyłączony</p>
            <h1 className="mt-2 text-3xl font-black tracking-normal sm:text-5xl">
              Tu nie pokazujemy przykładowych danych
            </h1>
            <p className="mt-4 max-w-2xl text-base font-semibold leading-7 text-[#5f5f5b]">
              W trybie OFF aplikacja korzysta z realnego API InPost i nie miesza lokalnie zasianych Paczkomatów
              z normalnymi wynikami. Włącz przełącznik, żeby zobaczyć scenariusze testowe.
            </p>
          </section>
        ) : null}

        {demoMode ? (
          <>
        <section className="rounded-xl border border-black/10 bg-white p-5 shadow-sm sm:p-7 lg:p-9">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-sm font-black uppercase text-[#5f5f5b]">Demo dla reviewera</p>
              <h1 className="mt-2 text-3xl font-black tracking-normal sm:text-5xl">
                Przykładowa historia niezawodności
              </h1>
              <p className="mt-4 text-base font-semibold leading-7 text-[#5f5f5b]">
                Te Paczkomaty są zasiane w lokalnej bazie komendą <code>npm run demo:history</code>.
                Dane są przykładowe i służą tylko do pokazania panelu Niezawodność bez czekania na kilka
                uruchomień collectora.
              </p>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-[#ffd200] bg-[#fff6bf] p-4 text-sm font-black">
              <DatabaseZap className="h-5 w-5 shrink-0" />
              Dane demo, nie realny monitoring
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-3">
          <Link
            href={detailHref(DEMO_CASES[0])}
            className="grid gap-4 rounded-xl border border-[#ffd200] bg-[#fff6bf] p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-[#1d1d1b] hover:shadow-md sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
          >
            <div>
              <p className="text-sm font-black uppercase text-[#5f5f5b]">Demo triage, alertów i alternatyw</p>
              <h2 className="mt-1 text-2xl font-black">SYZ01M pokazuje AI problem score i Plan B</h2>
              <p className="mt-2 text-sm font-semibold leading-6 text-[#3c3c3c]">
                Otwórz ten przypadek, żeby zobaczyć jak zapisane analizy AI zgłoszeń obniżają finalny score,
                podbijają risk i wzmacniają rekomendowaną alternatywę w pobliżu.
              </p>
            </div>
            <div className="flex items-center justify-between gap-3 sm:justify-end">
              <span className="text-sm font-black">Zobacz alert</span>
              <ChevronRight className="h-5 w-5" />
            </div>
          </Link>

          {DEMO_CASES.map((item) => (
            <Link
              key={item.name}
              href={detailHref(item)}
              className="grid gap-4 rounded-xl border border-black/10 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-[#1d1d1b] hover:shadow-md sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-black">{item.name}</h2>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${toneClass(item.tone)}`}>
                    {item.label}
                  </span>
                </div>
                <p className="mt-1 truncate text-base font-bold text-[#3c3c3c]">{item.address}</p>
                <p className="mt-1 text-sm font-semibold text-[#777770]">{item.description}</p>
              </div>
              <div className="flex items-center justify-between gap-3 sm:justify-end">
                <span className="text-sm font-black">Zobacz panel</span>
                <ChevronRight className="h-5 w-5" />
              </div>
            </Link>
          ))}
        </section>
          </>
        ) : null}
      </div>
    </main>
  );
}

function detailHref(item: DemoCase) {
  const params = new URLSearchParams({
    q: item.address,
    lat: String(item.lat),
    lng: String(item.lng),
    radius_m: "3000",
    demo: "true",
  });
  return `/points/PL/${item.name}?${params.toString()}`;
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function parseDemo(value: string | undefined) {
  return value === "true" || value === "1";
}

function toneClass(tone: DemoCase["tone"]) {
  if (tone === "good") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (tone === "ok") {
    return "border-[#ffd200] bg-[#fff4b8] text-[#1d1d1b]";
  }
  if (tone === "bad") {
    return "border-red-200 bg-red-50 text-red-800";
  }
  return "border-zinc-200 bg-zinc-100 text-zinc-700";
}
