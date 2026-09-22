# GCP Phase 6 — Forecasting (BigQuery ML)

Goal: a 6-month-ahead forecast for revenue and order volume, built the same
way every other governed capability in this project was built — a real,
inspectable object (a BigQuery ML model + a governed Gold table) rather than
a one-off chart, so the SQL Agent can answer "what do you project revenue to
look like next quarter" the same way it answers any other question: by
querying a Gold object that's in the context layer and the guardrail
allow-list. Direct GCP port of the Databricks build's Phase 7
(`docs/phase7_predictive_analytics_setup.md` there, Prophet + MLflow) — see
that doc's own "GCP alternative" note, which scoped this trade before the
GCP project even existed.

**Status: ready to run.** Delivered, not yet run in Cloud Shell.

## 0. Prerequisites

- Phase 5 done — governance layer + agent pipeline confirmed working
  against `clientgcpkraftheinzadpoc`.
- Nothing else — the forecast trains directly off `gold_monthly_kpis`,
  which Phase 4 already built and validated. No new IAM roles needed
  beyond what Phase 1-5 already granted (BigQuery Data Editor + Job User
  cover `CREATE MODEL`).

## 1. What this phase adds

- **`pipelines/forecast/sql/01_model_forecast_revenue.sql`,
  `02_model_forecast_orders.sql`** — two `CREATE MODEL ... ARIMA_PLUS`
  statements, one per metric, trained on `gold_monthly_kpis` with the
  current in-progress calendar month excluded (a partial month looks
  like a demand cliff to a forecasting model — the same instinct behind
  `gold_ytd_by_year`'s day-of-year cutoff, applied here instead to
  training data). `auto_arima = TRUE` lets BigQuery search orders itself,
  same as the Databricks build let Prophet fit its own seasonality.
- **`pipelines/forecast/sql/03_gold_sales_forecast.sql`** — unions each
  model's `ML.FORECAST(..., STRUCT(6 AS horizon, 0.9 AS confidence_level))`
  output with history into **`gold_sales_forecast`** (one row per
  metric x month; forecast rows carry `lower_bound`/`upper_bound` at a
  90% interval, historical rows don't) — the exact same table shape the
  Databricks build's Prophet notebook produces, so the downstream
  context-layer contract needed no changes beyond adding this table.
- **`pipelines/forecast/sql/04-06` + `run_forecast.py`'s backtest step**
  — a genuine holdout backtest: two backtest-only models trained with
  the last 6 known complete months held out, forecast those same 6
  months, and compare against the actuals `gold_monthly_kpis` already
  has for that window — MAPE/RMSE/MAE computed by hand in SQL, not just
  trusted. Simplified from the Databricks build's Prophet rolling-origin
  cross-validation (one holdout window here, not multiple rolling
  cutoffs) — named as a deliberate limitation, not missed; see
  "Known limitations" below.
- **`pipelines/forecast/run_forecast.py`** — runs 01-03 (production),
  computes the holdout cutoff date, then runs 04-06 (backtest) and
  prints the accuracy table. `--skip-backtest` runs only the production
  path if you want the forecast table fast without waiting on the
  backtest models too.
- **Governance wiring, already applied in this pass:**
  - `pipelines/governance/sql/02_authorized_views.sql` — 19th view,
    `authorized.gold_sales_forecast`.
  - `agents/guardrails.py` — `"gold_sales_forecast"` added to
    `ALLOWED_TABLES` (18 → **19**).
  - `context/schema_reference.yaml` — `gold_sales_forecast` added under
    `curated_views`, with its `is_forecast` semantics spelled out.
  - `context/metric_specs.yaml` — `revenue_forecast_usd` and
    `order_count_forecast` metric specs, both explicit that they're
    forward-looking only.
  - `context/business_glossary.yaml` — a new **Forecast** term + a rule
    never to substitute forecast rows for `gold_monthly_kpis`, and never
    to state a forecast without its range.
  - `context/example_questions.yaml` and `agents/demo_gemini.py` — the
    6th demo question, matching the Databricks build's question set
    exactly: *"What do you project revenue and order volume to look like
    over the next six months?"*
  - No change needed to `pipelines/governance/sql/01_validate_gold_sql.sql`
    — it already allows any `<project>.gold.*` object (minus
    `gold_dq_summary`), so a new Gold table passes validation without a
    guardrail code change. Same payoff Phase 5's setup doc already named:
    adding a capability is a data + context-layer change, not a
    re-audit of the validation function.

## 2. Run it — Cloud Shell

```bash
cd ~/auria-fashion-dashboard-gcp
git pull origin dev
source .venv/bin/activate   # if not already active
python pipelines/forecast/run_forecast.py --project clientgcpkraftheinzadpoc
```

This prints, in order: `OK` for each of the 6 SQL scripts, the
`gold_sales_forecast` row count, the computed holdout cutoff date, and the
backtest accuracy table (MAPE/RMSE/MAE per metric).

## 3. Validate

Sanity-check the forecast table directly:

```bash
bq query --use_legacy_sql=false \
  'SELECT * FROM `clientgcpkraftheinzadpoc.gold.gold_sales_forecast`
   WHERE is_forecast = true ORDER BY metric, month_date'
```

Expect 6 rows per metric (12 total), `lower_bound < value < upper_bound` on
every row, and the first forecast month for each metric equal to the
current in-progress calendar month (by design — see §1).

## 4. Verify end to end

Ask the demo script the new 6th question directly — it's already wired
into `agents/demo_gemini.py`'s `DEMO_QUESTIONS`, so a normal
`python agents/demo_gemini.py --project clientgcpkraftheinzadpoc` run now
exercises it along with the original 5. Confirm the SQL disclosed queries
`gold_sales_forecast` with `is_forecast = true`, and that the answer states
a range, not a single false-precision number.

## 5. Add a forecast tile to the dashboard (Phase 7)

Deferred to Phase 7 (Looker Studio): a line/area chart against
`gold_sales_forecast`, `month_date` on X, `value` on Y, split by
`is_forecast` (or `metric`, one tile per metric), with
`lower_bound`/`upper_bound` as a shaded range so history flows visibly
into the projected band — mirroring the tile already described for the
Databricks AI/BI dashboard.

## 6. Schedule the refresh

For the POC, re-running `run_forecast.py` manually after each demo data
refresh is enough — the model only needs retraining when a new complete
month of `gold_monthly_kpis` lands. For anything longer-lived: a BigQuery
scheduled query or a small Cloud Scheduler + Cloud Run job calling this
script, monthly.

## Known limitations, named on purpose

- **One model family, not a bake-off.** `ARIMA_PLUS` was chosen and used
  directly — the backtest validates that its forecast is reasonable, but
  there's no comparison against `AI.FORECAST`/TimesFM (the documented
  zero-shot alternative in `gcp_strategy.md` §6) to show `ARIMA_PLUS` is
  the *best* choice, only that it's a defensible one. Worth demoing
  side-by-side if the "is this proper ML" question comes up.
- **One holdout window, not rolling cross-validation.** The backtest
  trains once on history through a single cutoff and forecasts the held-
  out 6 months, unlike the Databricks build's Prophet `cross_validation`
  (multiple rolling cutoffs). Read `mape_pct`/`rmse`/`mae` as directionally
  honest, not a statistically tight error bound — the same "read it in
  context" caveat the Databricks doc named for its own backtest.
- **Manual regeneration, not a scheduled pipeline (yet).** Every other
  Gold object rebuilds via `run_gold.py`/`run_governance.py`; this table
  is regenerated by hand-running `run_forecast.py`, so `generated_at` is
  the only freshness signal until §6's scheduling is actually built.
- **Same identity/grant limitation as the rest of this POC.** Model
  training and table writes run under the calling user's own gcloud
  identity, not a dedicated service account — already named in
  `agents/guardrails.py`'s module docstring, and it applies here too.

## Report back

Paste (or describe): the `gold_sales_forecast` row count, the backtest
table, and whether the §3 sanity query shows `lower_bound < value <
upper_bound` on every forecast row. If that checks out, Phase 6 is done
and we move to Phase 7 (dashboard + frontend).
