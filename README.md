# LockerPulse

LockerPulse is a customer-first InPost point finder built for the InPost Software Development Internship assignment.

The idea is simple: when a user has a few parcel lockers nearby, the nearest one is not always the best one. LockerPulse uses the live InPost Global Points API, local reliability history, anonymous user reports, and optional AI triage to answer a more useful question:

> Which Paczkomat is the safest choice today?

## Live Project

- Landing page: [https://lockerpulse-web-production.up.railway.app](https://lockerpulse-web-production.up.railway.app)
- Customer app: [https://lockerpulse-web-production.up.railway.app/app](https://lockerpulse-web-production.up.railway.app/app)
- API health: [https://lockerpulse-api-production.up.railway.app/health](https://lockerpulse-api-production.up.railway.app/health)
- API docs: [https://lockerpulse-api-production.up.railway.app/docs](https://lockerpulse-api-production.up.railway.app/docs)

The old static screenshot was removed from the README because the UI changed significantly. The live links above are the source of truth for the current product experience.

## What It Does

LockerPulse is not a clone of the InPost website and not an official InPost status system. It is an extra decision layer built on top of public point data.

Current features:

- address search with realtime suggestions,
- live nearby Paczkomat search from the InPost API,
- adjustable search radius,
- simple ranked customer list with map context,
- detail page for each point,
- explainable `LockerPulse Score` from 0 to 100,
- local status snapshots stored in Postgres,
- reliability labels based on collected history,
- anonymous problem reports with required comment and optional photos,
- admin panel for viewing and deleting reports,
- risk advice: `ok`, `watch`, `risky`, `critical`,
- Plan B recommendations when a point looks risky,
- report triage that works with no model, local Ollama, or cloud models through LiteLLM.

There is no demo-data switch anymore. Search results come from the live InPost API. Local history and reports appear only after the collector runs or users submit reports.

## Product Flow

1. User enters an address.
2. Backend geocodes the address.
3. Backend searches InPost points around the coordinates.
4. Each point receives a transparent score.
5. The UI shows a short ranked list: point name, street, distance, status, score.
6. The detail page explains why the score is high or low.
7. If reports or history suggest risk, LockerPulse recommends a better nearby Plan B.

## Architecture

```txt
apps/
  api/        FastAPI backend, collectors, scoring, triage
  web/        Next.js App Router frontend
packages/
  database/   Prisma schema shared by backend commands
docs/
  api-exploration.md
  decisions.md
infra/
  compose.yaml
  docker/
    api.Dockerfile
    web.Dockerfile
scripts/
  explore_inpost_api.py
```

Stack:

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, SWR, Leaflet
- Backend: FastAPI, Pydantic, httpx, LiteLLM
- Database: Postgres + Prisma Client Python
- Local tooling: npm workspaces, uv, Docker Compose
- Deployment: Railway, separate API and web services

Important source files:

- Base scoring: [`apps/api/src/locker_pulse_api/services/scoring.py`](apps/api/src/locker_pulse_api/services/scoring.py)
- Score composition and final score: [`apps/api/src/locker_pulse_api/services/point_service.py`](apps/api/src/locker_pulse_api/services/point_service.py)
- Reliability scoring: [`apps/api/src/locker_pulse_api/services/reliability.py`](apps/api/src/locker_pulse_api/services/reliability.py)
- Report penalties: [`apps/api/src/locker_pulse_api/services/reports.py`](apps/api/src/locker_pulse_api/services/reports.py)
- Triage engines: [`apps/api/src/locker_pulse_api/services/report_triage_engines.py`](apps/api/src/locker_pulse_api/services/report_triage_engines.py)
- AI agent prompt: [`apps/api/prompts/report_triage_agent.md`](apps/api/prompts/report_triage_agent.md)

## Scoring Deep Dive

The visible score is a final customer score, not just a raw API score.

```txt
raw_live_score = status + distance + 24/7 + accessibility + functions + hardware + data_quality
base_score = status_cap(raw_live_score + history_adjustment)
community_penalty = fresh saved report-analysis penalties from last 24h, capped at 35
final_score = status_cap(base_score - community_penalty)
```

`PointSummary.score` returned by the API is the final score. The API also exposes helper fields such as `base_score`, `community_penalty`, `problem_score_24h`, `reasons`, `warnings`, and `problem_reasons`.

### Base Live Score

| Signal | Points | Why it matters |
| --- | ---: | --- |
| Current status is `Operating` | `+35` | A point that is not operating should never look like a great choice. |
| Distance inside selected radius | `0-20` | Closer is better, but distance is not the whole decision. |
| `location_247=true` | `+15` | 24/7 access is valuable for normal customers. |
| `easy_access_zone=true` | `+10` | Easier access means fewer surprises on arrival. |
| Required functions supported | `+10` | If user needs collect/send, the point should support it. |
| Modern physical type: `next`, `newfm`, `modular` | `+5` | Newer devices are treated as a small positive signal. |
| Public details are complete: image plus readable address/description | `+5` | Better data quality means more trust in the recommendation. |

Distance is calculated proportionally:

```txt
distance_score = 20 * (1 - min(distance_m, radius_m) / radius_m)
```

So a point very close to the searched address can get almost `20`, while a point near the radius edge gets close to `0`.

### Score Caps

Status can cap the score after other positive signals:

| Status | Max score |
| --- | ---: |
| `Operating` | no cap |
| `Disabled` | `25` |
| any other non-operating or unknown status, for example `Created` | `45` |

This prevents a disabled point from looking good only because it is close or has nice metadata.

### Grades

| Score | Grade |
| ---: | --- |
| `90-100` | `excellent` |
| `75-89` | `good` |
| `60-74` | `fair` |
| `40-59` | `weak` |
| `0-39` | `critical` |

### What Creates A High Score?

A high score usually means:

- the point is currently `Operating`,
- it is close to the searched address,
- it is available 24/7,
- it has easy access,
- it supports core parcel actions,
- it has a modern physical type,
- it has a readable address and image,
- recent history is stable,
- there are no fresh credible user reports.

### What Creates A Low Score?

A low score usually means one or more of these:

- the point is `Disabled` or not yet fully active,
- it is far away within the selected radius,
- it is not marked as 24/7,
- it is not marked as easy access,
- supported functions are incomplete,
- public details are incomplete,
- history shows a recent problem or frequent status changes,
- fresh user reports suggest a real issue.

Important caveat: `locker_availability=NO_DATA` does not lower the score. API exploration showed that this field is often unavailable, so treating `NO_DATA` as a failure would create false negatives. LockerPulse displays it as a warning instead.

## Reliability History

The collector can fetch point data repeatedly and store `PointSnapshot` and `PointStatusEvent` rows in Postgres.

Reliability is calculated from recent snapshots:

| Label | Meaning | Score adjustment |
| --- | --- | ---: |
| `brak historii` | not enough snapshots | `0` |
| `stabilny` | uptime at least `98%`, no status changes | `+3` |
| `raczej stabilny` | uptime at least `90%`, max 2 status changes | `+1` |
| `problem` | latest snapshot is not `Operating` | `-20` |
| `niestabilny` | frequent changes or poor uptime | `-10` |

No history is neutral. The app does not punish a point just because the local collector has not seen it enough times yet.

## User Reports And Community Penalty

Users can report a problem from the point detail page. A report includes:

- reason: `not_working`, `full`, `screen_problem`, `access_problem`, `other`,
- required comment, 10-500 characters,
- optional photos, up to 3 images.

Each report gets analyzed exactly once and the result is stored in `UserReportAnalysis`.

Only stored analyses from the last 24 hours affect the current score. Search/detail endpoints do not call a model. They only read already saved analysis rows.

Valid analyses are those with:

- `status="ok"`,
- `isActionable=true`,
- `confidence >= 0.35`,
- category not equal to `spam`,
- `spamLikelihood < 0.8`.

Penalty scale:

| Analysis result | Penalty |
| --- | ---: |
| severity `<25`, low confidence, spam, high spam likelihood, or not actionable | `0` |
| severity `25-45` | `5` |
| severity `46-65` | `10` |
| severity `66-85` | `20` |
| severity `86-100` | `30` |

Community penalty is currently:

```txt
community_penalty = min(35, sum(score_penalty for valid analyses from last 24h))
```

This makes the UI understandable: if admin sees a saved report penalty of `-5`, the detail page shows `-5` unless there are additional fresh valid reports.

## AI Triage System

The triage system is provider-agnostic:

- no model configured: deterministic rules,
- local model: Ollama through LiteLLM,
- cloud model: OpenAI, Gemini, Anthropic, or another LiteLLM-supported provider,
- model failure: rules fallback, not a broken report.

The agent prompt lives here: [`apps/api/prompts/report_triage_agent.md`](apps/api/prompts/report_triage_agent.md).

The agent role:

> Evaluate an anonymous report about an InPost point and estimate customer-facing risk. Do not change official InPost status.

The model receives:

- report reason,
- user comment,
- optional photos if allowed,
- point context,
- current score,
- reliability label,
- recent report summary.

The comment is treated as untrusted data. Prompt-injection attempts inside a report must be ignored.

The model must return strict JSON:

```json
{
  "severity": 0,
  "confidence": 0.0,
  "category": "unclear",
  "is_actionable": true,
  "spam_likelihood": 0.0,
  "photo_evidence": "none",
  "recommended_risk_floor": "none",
  "score_penalty": 0,
  "summary": "Krótki opis po polsku",
  "evidence": ["konkretny powód decyzji"]
}
```

The application validates the JSON with Pydantic and recomputes `score_penalty` itself. The model can recommend a penalty, but the backend owns the final penalty mapping.

Severity guide:

| Severity | Meaning |
| ---: | --- |
| `0-10` | spam, joke, unrelated, no real issue |
| `11-25` | cosmetic or small inconvenience |
| `26-45` | light issue worth a warning |
| `46-65` | functional issue, point may be risky |
| `66-85` | serious issue, recommend Plan B |
| `86-100` | critical issue, likely unusable or safety-relevant |

Rule fallback values:

| Reason / signal | Severity | Confidence | Risk floor | Typical penalty |
| --- | ---: | ---: | --- | ---: |
| safety words like `kable`, `iskry`, `zagrożenie`, `pożar` | `90` | `0.86` | `critical` | `30` |
| `not_working` | `78` | `0.78` | `risky` | `20` |
| `full` | `64` | `0.74` | `risky` | `10` |
| `screen_problem` | `58` | `0.72` | `risky` | `10` |
| `access_problem` | `55` | `0.72` | `risky` | `10` |
| `other` | `35` | `0.65` | `watch` | `5` |

This means the application can run on Railway without Ollama or API keys. AI is an enhancement, not a hard dependency.

## Running Locally

Requirements:

- Node.js 20.9+
- npm 10+
- Python 3.10+; Python 3.12 is recommended
- uv
- Docker
- Optional: Ollama with `gemma3:4b`

Install dependencies and create the env file:

```bash
npm install
uv sync --project apps/api
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Start Postgres, generate Prisma Client Python, and push the schema:

```bash
docker compose --env-file .env -f infra/compose.yaml up -d
npm run db:generate
npm run db:push
```

Run the full app:

```bash
npm run dev
```

Open:

- frontend: [http://localhost:3000](http://localhost:3000)
- customer app: [http://localhost:3000/app](http://localhost:3000/app)
- backend OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- admin reports: [http://localhost:3000/admin](http://localhost:3000/admin)

## Triage Configuration

Default production-safe mode:

```env
REPORT_TRIAGE_PROVIDER="auto"
REPORT_TRIAGE_MODEL=""
REPORT_TRIAGE_API_BASE=""
```

This uses deterministic rules and needs no model.

Local Ollama mode:

```bash
ollama serve
ollama pull gemma3:4b
ollama list
```

```env
REPORT_TRIAGE_PROVIDER="litellm"
REPORT_TRIAGE_MODEL="ollama_chat/gemma3:4b"
REPORT_TRIAGE_API_BASE="http://127.0.0.1:11434"
```

Cloud provider example:

```env
REPORT_TRIAGE_PROVIDER="litellm"
REPORT_TRIAGE_MODEL="openai/gpt-4o-mini"
OPENAI_API_KEY="..."
```

Provider keys stay on the backend only. They are never entered in the browser. Photos are not sent to cloud models unless `REPORT_TRIAGE_ALLOW_CLOUD_PHOTOS=true`.

Analyze pending reports manually:

```bash
npm run reports:analyze-pending
```

## Collector

Collect status history once:

```bash
npm run collector:once
```

Run the collector in a loop:

```bash
npm run collector:loop
```

The default collector uses a small watchlist so the project does not aggressively crawl the full InPost network.

## API Examples

Geocode an address:

```bash
curl "http://127.0.0.1:8000/api/v1/geocode?q=Dluga%201,%20Gdansk"
```

Search nearby points:

```bash
curl "http://127.0.0.1:8000/api/v1/points/search?lat=52.2297&lng=21.0122&radius_m=3000&functions=parcel_collect,parcel_send"
```

Get recent point history:

```bash
curl "http://127.0.0.1:8000/api/v1/points/PL/GDA65M/history?days=7"
```

Get safer alternatives:

```bash
curl "http://127.0.0.1:8000/api/v1/points/PL/GDA65M/alternatives?lat=54.3495&lng=18.6481&radius_m=3000"
```

Submit a report:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/points/PL/GDA65M/reports" \
  -H "Content-Type: application/json" \
  -d "{\"reason\":\"screen_problem\",\"comment\":\"Ekran nie reaguje na dotyk przez kilka prób.\"}"
```

Inspect stored analysis:

```bash
curl "http://127.0.0.1:8000/api/v1/reports/<report_id>/analysis"
```

Admin reports:

```bash
curl "http://127.0.0.1:8000/api/v1/admin/reports"
curl -X DELETE "http://127.0.0.1:8000/api/v1/admin/reports/<report_id>"
```

If `ADMIN_TOKEN` is set, admin requests must include `X-Admin-Token`.

## Docker

Build API:

```bash
docker build -f infra/docker/api.Dockerfile -t lockerpulse-api .
```

Run API:

```bash
docker run --rm --env-file .env -p 8000:8000 lockerpulse-api
```

Build web:

```bash
docker build -f infra/docker/web.Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 \
  -t lockerpulse-web .
```

Run web:

```bash
docker run --rm -p 3000:3000 lockerpulse-web
```

## Railway Deployment

Production shape:

- `lockerpulse-api`: FastAPI from `infra/docker/api.Dockerfile`
- `lockerpulse-web`: Next.js from `infra/docker/web.Dockerfile`
- Postgres database

API variables:

```env
DATABASE_URL="${{Postgres.DATABASE_URL}}"
WEB_ORIGIN="https://<web-domain>"
RUN_DB_PUSH_ON_START="true"
INPOST_API_BASE_URL="https://api-global-points.easypack24.net/v1"
INPOST_REQUEST_TIMEOUT_SECONDS="10"
NOMINATIM_API_BASE_URL="https://nominatim.openstreetmap.org"
REPORT_TRIAGE_PROVIDER="auto"
REPORT_TRIAGE_MODEL=""
REPORT_TRIAGE_API_BASE=""
REPORT_TRIAGE_ALLOW_CLOUD_PHOTOS="false"
ADMIN_TOKEN="<strong-random-token>"
```

Web variables:

```env
NEXT_PUBLIC_API_BASE_URL="https://<api-domain>"
```

Useful CLI commands:

```bash
npx railway whoami
npx railway link
npx railway service status --service lockerpulse-api
npx railway service status --service lockerpulse-web
npx railway logs --service lockerpulse-api
npx railway logs --service lockerpulse-web
```

## Data Caveats

- LockerPulse does not know real-time compartment occupancy.
- User reports are anonymous helper signals, not official InPost data.
- AI triage never changes the official InPost status.
- `NO_DATA` in `locker_availability` is shown as uncertainty, not treated as a failure.
- Full Europe-wide crawling, subscriptions, notifications, and PDF reports are intentionally out of scope.

## Testing

Backend tests:

```bash
uv run --project apps/api pytest
```

Frontend checks:

```bash
npm run lint --workspace apps/web
npm run build --workspace apps/web
```

Full check:

```bash
npm test
```

## API Exploration

Run:

```bash
npm run explore:api
```

This writes [`docs/api-exploration.md`](docs/api-exploration.md) using live InPost API data.
