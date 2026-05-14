import Link from "next/link";
import {
  ArrowRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Database,
  Flag,
  MapPin,
  Radar,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";
import { LandingModelViewer } from "./landing-model-viewer";
import { LandingVideoPlayer } from "./landing-video-player";

const FLOW_STEPS = [
  {
    title: "API InPost",
    description: "Pobieramy realne punkty, status, funkcje, współrzędne i dane adresowe.",
    icon: Database,
  },
  {
    title: "Score i historia",
    description: "Łączymy aktualny stan z lokalną historią snapshotów i zmian statusu.",
    icon: Radar,
  },
  {
    title: "Zgłoszenia",
    description: "Użytkownik może opisać problem i dodać zdjęcia bez zakładania konta.",
    icon: ShieldAlert,
  },
  {
    title: "Triage zgłoszeń",
    description: "Reguły albo skonfigurowany model oceniają wagę zgłoszenia raz i nie zmieniają oficjalnego statusu.",
    icon: BrainCircuit,
  },
  {
    title: "Plan B",
    description: "Gdy punkt wygląda ryzykownie, LockerPulse proponuje lepszą alternatywę w pobliżu.",
    icon: Flag,
  },
];

const TECH_STACK = [
  "Next.js App Router",
  "FastAPI",
  "Prisma ORM",
  "Postgres",
  "InPost Points API",
  "LiteLLM / rules fallback",
  "Tailwind CSS",
];

const AGENT_SIGNALS = [
  { label: "Severity", value: "78/100", tone: "bg-red-50 border-red-200 text-red-800" },
  { label: "Confidence", value: "82%", tone: "bg-emerald-50 border-emerald-200 text-emerald-800" },
  { label: "Penalty", value: "-20 pkt", tone: "bg-[#fff4b8] border-[#ffd200] text-[#1d1d1b]" },
  { label: "Risk floor", value: "Ryzyko", tone: "bg-orange-50 border-orange-200 text-orange-800" },
];

export function LandingPage() {
  return (
    <main className="min-h-screen overflow-hidden bg-[#f4f4f2] text-[#1d1d1b]">
      <LandingHeader />

      <section className="relative border-b border-black/10 bg-[#ffd200]">
        <div className="absolute inset-0 landing-hero-pattern opacity-45" aria-hidden="true" />
        <div className="relative mx-auto grid w-full max-w-7xl gap-8 px-4 py-6 sm:px-6 lg:py-10">
          <LandingVideoPlayer />

          <div className="mx-auto w-full max-w-4xl">
            <div className="flex flex-col justify-between rounded-2xl border border-black/10 bg-white p-6 shadow-xl sm:p-8 lg:min-h-[420px]">
              <div className="mb-7">
                <LandingModelViewer />
              </div>
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-[#ffd200] px-3 py-1.5 text-xs font-black uppercase">
                  <Sparkles className="h-4 w-4" />
                  InPost-inspired technical showcase
                </div>
                <h1 className="mt-5 max-w-3xl text-4xl font-black leading-[0.95] tracking-normal sm:text-6xl lg:text-7xl">
                  LockerPulse wie, który Paczkomat ma sens dzisiaj.
                </h1>
                <p className="mt-5 max-w-2xl text-base font-semibold leading-7 text-[#3c3c3c] sm:text-lg">
                  Aplikacja bierze realne dane z API InPost, dodaje historię działania, zgłoszenia użytkowników
                  i ocenę zgłoszeń, żeby polecić punkt albo pokazać Plan B.
                </p>
              </div>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/app"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-[#1d1d1b] px-5 text-sm font-black text-white transition hover:-translate-y-0.5 hover:bg-black"
                >
                  Sprawdź Paczkomat
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/app"
                  className="inline-flex h-12 items-center justify-center gap-2 rounded-md border border-black/15 bg-[#ffd200] px-5 text-sm font-black text-[#1d1d1b] transition hover:-translate-y-0.5 hover:bg-[#f0c400]"
                >
                  Zobacz triage zgłoszeń
                  <Bot className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <HowItWorksSection />
      <AiAgentSection />
      <CustomerFlowSection />
      <TechStackSection />
      <FinalCtaSection />
    </main>
  );
}

function LandingHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-black/10 bg-white/92 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3" aria-label="LockerPulse landing">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-[#ffd200] font-black text-[#1d1d1b]">
            LP
          </span>
          <span className="text-lg font-black tracking-normal">LockerPulse</span>
        </Link>
        <nav className="hidden items-center gap-5 text-sm font-black text-[#3c3c3c] md:flex">
          <a href="#jak-dziala" className="hover:text-[#1d1d1b]">Jak działa</a>
          <a href="#ai-agent" className="hover:text-[#1d1d1b]">Triage</a>
          <a href="#technicznie" className="hover:text-[#1d1d1b]">Technicznie</a>
        </nav>
        <Link
          href="/app"
          className="inline-flex h-10 items-center justify-center rounded-md bg-[#1d1d1b] px-4 text-sm font-black text-white transition hover:bg-black"
        >
          Otwórz appkę
        </Link>
      </div>
    </header>
  );
}

function HowItWorksSection() {
  return (
    <section id="jak-dziala" className="bg-white py-16 sm:py-20">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6">
        <SectionIntro
          eyebrow="Jak działa"
          title="Od surowego API do decyzji klienta."
          description="LockerPulse nie udaje oficjalnego statusu InPost. Dokłada własną warstwę interpretacji: score, historię, community signal i rekomendację alternatywy."
        />
        <div className="mt-10 grid gap-4 md:grid-cols-5">
          {FLOW_STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <article
                key={step.title}
                className="landing-reveal group relative overflow-hidden rounded-xl border border-black/10 bg-[#f8f8f6] p-5 shadow-sm transition hover:-translate-y-1 hover:border-[#ffd200] hover:shadow-md"
                style={{ animationDelay: `${index * 90}ms` }}
              >
                <div className="absolute right-4 top-4 font-mono text-xs font-black text-black/20">
                  0{index + 1}
                </div>
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-md bg-[#ffd200]">
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="mt-5 text-lg font-black">{step.title}</h3>
                <p className="mt-3 text-sm font-semibold leading-6 text-[#5f5f5b]">{step.description}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function AiAgentSection() {
  return (
    <section id="ai-agent" className="border-y border-black/10 bg-[#11110f] py-16 text-white sm:py-20">
      <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div>
          <p className="text-sm font-black uppercase text-[#ffd200]">Report Triage</p>
          <h2 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">
            Model jest opcjonalny, a decyzja i tak zapisuje się tylko raz.
          </h2>
          <p className="mt-5 text-base font-semibold leading-7 text-white/72">
            Bez API key działa analiza regułowa. Po skonfigurowaniu LiteLLM ten sam kontrakt obsługuje Ollamę,
            OpenAI, Gemini, Anthropic i inne providery, a aplikacja sama liczy penalty.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {["rules fallback", "structured JSON", "LiteLLM providers", "no official status override"].map((item) => (
              <span key={item} className="rounded-full border border-[#ffd200]/25 bg-[#ffd200]/10 px-3 py-1.5 text-xs font-black uppercase text-[#ffd200]">
                {item}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-[#ffd200]/25 bg-white/[0.04] p-4 shadow-2xl backdrop-blur">
          <div className="grid gap-3 rounded-xl border border-white/10 bg-black/35 p-4 font-mono text-xs leading-6 text-white/80">
            <div className="text-[#ffd200]">INPUT_JSON</div>
            <div>{"{ reason: 'screen_problem', comment: 'ekran nie reaguje...', photos: 1 }"}</div>
            <div className="landing-scan-line h-px bg-[#ffd200]" />
            <div className="text-[#ffd200]">TRIAGE_OUTPUT</div>
            <div>{"{ severity: 78, confidence: 0.82, risk_floor: 'risky' }"}</div>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            {AGENT_SIGNALS.map((item) => (
              <div key={item.label} className={`rounded-xl border p-4 ${item.tone}`}>
                <p className="text-xs font-black uppercase opacity-70">{item.label}</p>
                <p className="mt-2 text-xl font-black">{item.value}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-[#ffd200] bg-[#fff6bf] p-4 text-[#1d1d1b]">
            <p className="text-xs font-black uppercase">Efekt dla klienta</p>
            <p className="mt-1 text-lg font-black">Score spada z 92 do 72 i pojawia się Plan B.</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function CustomerFlowSection() {
  const steps = [
    ["Wpisz adres", "Realtime geocoding podpowiada ulice i od razu szuka punktów."],
    ["Wybierz punkt", "Lista pokazuje tylko to, co klient rozumie: adres, status, score."],
    ["Sprawdź ryzyko", "Szczegóły tłumaczą historię, alerty i community signal."],
    ["Zgłoś problem", "Modal przyjmuje komentarz i zdjęcia, a system ocenia wagę zgłoszenia."],
  ];

  return (
    <section className="bg-[#f4f4f2] py-16 sm:py-20">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6">
        <SectionIntro
          eyebrow="Customer flow"
          title="UX dla osoby, która po prostu chce odebrać paczkę."
          description="Landing opowiada technologię, ale produkt zostaje prosty: adres, lista, szczegóły i decyzja."
        />
        <div className="mt-10 grid gap-4 lg:grid-cols-4">
          {steps.map(([title, description], index) => (
            <article key={title} className="rounded-xl border border-black/10 bg-white p-5 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#1d1d1b] font-mono text-sm font-black text-white">
                {index + 1}
              </div>
              <h3 className="mt-5 text-xl font-black">{title}</h3>
              <p className="mt-3 text-sm font-semibold leading-6 text-[#5f5f5b]">{description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function TechStackSection() {
  return (
    <section id="technicznie" className="bg-white py-16 sm:py-20">
      <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
        <SectionIntro
          eyebrow="Technicznie"
          title="Pełny stack, ale bez udawania enterprise na siłę."
          description="Monorepo pokazuje frontend, backend, bazę, collector, scoring, raporty użytkowników i lokalny model AI."
        />
        <div className="grid gap-3 sm:grid-cols-2">
          {TECH_STACK.map((item) => (
            <div key={item} className="flex items-center gap-3 rounded-xl border border-black/10 bg-[#f8f8f6] p-4">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-700" />
              <span className="text-sm font-black">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FinalCtaSection() {
  return (
    <section className="bg-[#ffd200] py-14">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm font-black uppercase text-[#5f5f5b]">Gotowe do sprawdzenia</p>
          <h2 className="mt-2 text-3xl font-black sm:text-5xl">Przejdź do działającej aplikacji.</h2>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link href="/app" className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-[#1d1d1b] px-5 text-sm font-black text-white transition hover:bg-black">
            Sprawdź Paczkomat
            <MapPin className="h-4 w-4" />
          </Link>
          <Link href="/app" className="inline-flex h-12 items-center justify-center gap-2 rounded-md border border-black/15 bg-white px-5 text-sm font-black text-[#1d1d1b] transition hover:bg-[#f8f8f6]">
            Zobacz analizę zgłoszeń
            <Zap className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}

function SectionIntro({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="max-w-3xl">
      <p className="text-sm font-black uppercase text-[#5f5f5b]">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">{title}</h2>
      <p className="mt-4 text-base font-semibold leading-7 text-[#5f5f5b]">{description}</p>
    </div>
  );
}
