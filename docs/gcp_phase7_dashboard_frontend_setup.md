# GCP Phase 7 — Native Dashboard + Frontend

Goal: a Next.js app with a real, in-app dashboard (KPI cards + Recharts
charts + tables, built from live BigQuery data) and an "Ask a question"
sidebar wired to the Phase 5 agent pipeline, deployed as its own Cloud Run
service alongside the backend.

**Status: delivered, not yet deployed.** Code and CI/CD wiring committed
to `dev`; awaiting your push + Cloud Build run + report-back.

## 0. Decision change from the original plan — read this first

`gcp_strategy.md` section 7 originally scoped this phase as an embedded
Looker Studio report (the direct analogue of the Databricks build's
embedded AI/BI Dashboard). **That's been replaced**, at your explicit
request: Looker Studio is locked to its own light theme with no dark-mode
override, so a dark/colorful in-app design could never actually apply to
it — embedding it would mean the same "light widget bolted onto a dark
shell" compromise the Databricks build's frontend had to accept and name
as a limitation. Building the dashboard natively in Next.js (Recharts)
means the whole page, charts included, is one consistent, fully
themeable system. `gcp_strategy.md` section 7 and the Phase 7 row in
section 9 are updated to reflect this.

## 1. What this phase adds

**Backend (`app/`) — no longer a walking skeleton:**
- `app/bq.py` — a small helper that runs fixed, developer-authored SQL
  against the `authorized` dataset (never raw `gold`, same governed
  surface the chat sidebar's agent-drafted queries use) and returns
  JSON-ready rows. Deliberately NOT routed through
  `agents/guardrails.py`'s `validate()` — that function exists to check
  SQL the model drafted; this SQL is fixed and developer-written, so
  there's nothing for a guardrail to check.
- `app/main.py` — `POST /api/ask` (the Phase 5 agent pipeline over HTTP,
  same request/response contract the Databricks build's `backend/main.py`
  used) plus 7 `GET /api/dashboard/*` endpoints, one per tile: monthly
  KPIs, YTD, forecast, top products, top customers, returns by product,
  channel performance, supplier performance.
- `app/Dockerfile` now builds from the **repo root** as context (see
  `cloudbuild.yaml`), not `./app` alone — this lets it `COPY` the repo
  root's `agents/` and `context/` packages directly. No vendored-copy-
  and-sync-script trick like the Databricks build's `backend/` needed
  (that existed only to work around Vercel's per-project file tracing;
  Cloud Build has no such restriction).

**Frontend (`frontend/`) — no longer empty:**
- A full Next.js 15 App Router app, forked from the Databricks build's
  frontend shell (same `Filters` type, same chat message flow) but with
  `DashboardEmbed.tsx` replaced entirely by native components:
  `KpiCards`, `RevenueForecastChart`, `MarginReturnChart`,
  `ChannelPerformanceChart`, `TopProductsTable`, `TopCustomersTable`,
  `SupplierPerformanceTable` — all in `frontend/components/`, all reading
  from the backend's new `/api/dashboard/*` endpoints.
- **Dark, colorful theme** (`frontend/app/globals.css`): near-black navy
  background with soft purple/pink/cyan radial glows, a purple → pink →
  amber gradient hero header, glassmorphism-style cards, and a chart
  palette (`frontend/lib/palette.ts`) shared by every chart so the whole
  page reads as one system rather than a dark shell wrapped around
  someone else's light widget.
- **No `NEXT_PUBLIC_BACKEND_URL` and no CORS setup at all** — a
  deliberate simplification over the Databricks build's frontend. Two
  server-side Next.js Route Handlers (`app/api/ask/route.ts`,
  `app/api/dashboard/[...path]/route.ts`) proxy the browser's same-origin
  fetches to the FastAPI backend using `BACKEND_URL`, a **runtime-only**
  env var the browser never sees. This also sidesteps the "which domain
  do I allow-list" dance the Databricks build's `FRONTEND_ORIGIN` CORS
  setup needed.
- `frontend/Dockerfile` — multi-stage build to a standalone Next.js
  server (`next.config.mjs`'s `output: "standalone"`), also built from
  the repo root as context.
- Verified locally in this pass: `npm install && npm run build` completed
  clean (TypeScript + lint pass, 5/5 pages generated) before this was
  committed.

**`cloudbuild.yaml` — now builds and deploys both services:**
1. Build/push/deploy the backend (`auria-backend-${_ENV}`), same as
   before but from the new repo-root context.
2. Capture the deployed backend's URL (`gcloud run services describe`).
3. Build/push/deploy the frontend (`auria-frontend-${_ENV}`), setting
   `BACKEND_URL` to that captured URL at deploy time — this is *runtime*
   configuration, not baked into the Docker image, which is what avoids
   the chicken-and-egg problem of not knowing a Cloud Run service's URL
   before its first deploy.

## 2. One-time GCP setup — do this before your first push

The backend now runs as an actual Cloud Run **service**, not a script you
run yourself from Cloud Shell under your own gcloud identity. Unless you
specify otherwise, Cloud Run services run as the **default Compute Engine
service account**, which does **not** yet have the BigQuery/Vertex AI
roles your own identity has. Grant them once, from Cloud Shell:

```bash
PROJECT_ID=clientgcpkraftheinzadpoc
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA}" --role="roles/bigquery.dataViewer"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA}" --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA}" --role="roles/aiplatform.user"
```

Without this, every `/api/ask` and `/api/dashboard/*` call will 403 once
deployed, even though everything worked fine in Cloud Shell — the same
"which identity is actually calling BigQuery" gotcha named in
`agents/guardrails.py`'s module docstring, just showing up at the Cloud
Run layer instead of the notebook/script layer this time.

## 3. Deploy it

Unlike every prior phase, there's no script to run in Cloud Shell here —
this phase's "run it" is a **git push**, since Phase 0 already wired
`dev`/`main` pushes to Cloud Build triggers.

```bash
cd ~/Desktop/kh_github_work/auria-fashion-dashboard-gcp   # your Mac terminal, not Cloud Shell
git push origin dev
```

Then in the GCP Console: **Cloud Build → History**, watch the `dev`
trigger's build run through `build-backend` → `deploy-backend` →
`get-backend-url` → `build-frontend` → `deploy-frontend`. On success:
**Cloud Run** will show two new services, `auria-backend-dev` and
`auria-frontend-dev` — open the frontend service's URL.

## 4. Validate

1. The dashboard loads with real numbers in the KPI row and every chart/
   table — not loading placeholders, not an error banner.
2. The revenue chart shows history flowing into the 6-month forecast
   band (Phase 6's `gold_sales_forecast`, confirmed correct there).
3. Click a suggested question in the chat sidebar — confirm SQL
   disclosed, a rationale, and a real answer (not a 502 from the proxy
   route, which would mean `BACKEND_URL` or the IAM grants in §2 aren't
   right yet).
4. Set a region filter, ask a revenue question, confirm the drafted SQL
   reflects it — the completion check this phase inherits from
   `gcp_strategy.md`'s original Phase 6/7 bar. (The dashboard tiles
   themselves are not filter-scoped yet — see "Known limitations.")

## 5. Local testing (optional, before deploying)

**Backend:**
```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AURIA_GCP_PROJECT=clientgcpkraftheinzadpoc
export AURIA_GCP_LOCATION=us-central1
# needs `gcloud auth application-default login` done once, same ADC
# every prior phase's Cloud Shell script relied on
uvicorn main:app --reload --port 8000
```

**Frontend**, in a second terminal:
```bash
cd frontend
npm install
BACKEND_URL=http://localhost:8000 npm run dev
```
Open `http://localhost:3000`.

## Known limitations, named on purpose

- **Dashboard tiles aren't filter-scoped yet.** The `FilterBar` fully
  drives the chat sidebar (per the inherited completion check in §4), but
  none of the 7 dashboard endpoints accept region/channel/date params
  yet — they show all-time or current-year data regardless of the filter
  bar. A natural next-round enhancement (start with
  `channel-performance`, which already has both dimensions), not an
  oversight; named the same way the Databricks build named its embed's
  best-effort, one-directional filter sync.
- **No multi-turn chat memory**, same MVP simplification the Databricks
  build's Phase 6 named — `history` is always sent as `null`.
- **Runtime service-account grant is manual, one-time, and not
  Terraform'd.** Same POC-scale simplification named throughout this
  project (Phase 0's own IAM gotcha, `agents/guardrails.py`'s docstring)
  — a real production build would manage this as code, not a Cloud
  Shell command run once and forgotten.
- **Backend has no request auth.** `--allow-unauthenticated` on both
  Cloud Run services, matching every prior phase's "demo dataset, no
  sensitive data, no write path" posture — not something to carry into a
  real production deployment as-is.

## Report back

Paste (or describe): whether the Cloud Build run in §3 went green through
all 5 steps, whether the §4 checks pass on the live frontend URL, and if
not, which step/check failed. If both hold, Phase 7 is done and we move
to Phase 8 (polish: README, architecture diagram, demo recording, final
cost report).
