# GCP Phase 4 — Gold Star Schema Setup Guide

Goal: turn the 14 `silver_*` tables into a star schema (7 `dim_*`
dimensions, 4 `fct_*` facts) plus 7 curated `gold_*` reporting views that
answer the dashboard's actual questions directly, and prove Gold ties back
to Silver — same job as the Databricks build's Lakeflow pipeline, ported
to plain BigQuery SQL.

**Status: ready to run.** All 19 SQL scripts (7 `dim_*` + 4 `fct_*` + 7
`gold_*` + `gold_dq_summary`) and the Python runner are committed to
`dev`.

## Decisions this phase locks in (identical to the Databricks build)

- **Natural keys, not surrogate keys** — every dimension is keyed by its
  already-unique Silver id; no SCD history to version in a fully-
  recomputed batch dataset.
- **Cancelled orders stay in `fct_order_items`**, filtered out in every
  curated `gold_*` view (`order_status = 'Completed'`) — the raw fact
  still supports a cancellation-rate analysis without going back to
  Silver.
- **Returns are their own fact** (`fct_returns`), never netted into
  `fct_order_items`.
- **Aggregate views are keyed by id only** (e.g. `gold_top_products_monthly`
  has `product_id`, not `product_name`) — join to the matching `dim_*` for
  anything descriptive.
- **Revenue attributes to the customer's home region**, not the store's,
  regardless of channel (Online has no store at all).
- **`gold_ytd_by_year`** cuts every year off at the same day-of-year (the
  latest day-of-year actually present in the most recent year, computed
  via two window functions — not a dataset-wide max, which would just
  pick up December 31 from any complete prior year), so a partial current
  year compares fairly against prior full years.

**Known limitation, called out on purpose:** `fct_order_items.line_cogs_usd`
uses each product's *current* `unit_cost_usd` — Silver/Bronze don't carry a
cost-as-of-order-date history, so margin on an order placed when a
product's cost was different will be slightly off. Not worth a real
cost-history table for this demo dataset, where costs don't change during
the generated window anyway.

## What's different from the Databricks version, and what isn't

Same mapping pattern as Phase 3: every rule carries over identically,
only the mechanism changes (19 plain `.sql` scripts run in order by
`pipelines/gold/run_gold.py`, instead of one Lakeflow pipeline file with
`@dlt.table` decorators).

## Run it — Cloud Shell

```bash
cd ~/auria-fashion-dashboard-gcp
git pull origin dev
source .venv/bin/activate   # if not already active
python pipelines/gold/run_gold.py --project clientgcpkraftheinzadpoc
```

This produces 19 tables under `clientgcpkraftheinzadpoc.gold`: `dim_customer`,
`dim_product`, `dim_supplier`, `dim_store`, `dim_warehouse`, `dim_promotion`,
`dim_date`, `fct_order_items`, `fct_returns`, `fct_purchase_order_lines`,
`fct_inventory_snapshots`, `gold_monthly_kpis`, `gold_ytd_by_year`,
`gold_top_products_monthly`, `gold_top_customers_monthly`,
`gold_returns_by_product_monthly`, `gold_channel_performance`,
`gold_supplier_performance`, and `gold_dq_summary`.

## Validate

Reconciliation first:

```bash
bq query --use_legacy_sql=false \
  'SELECT * FROM `clientgcpkraftheinzadpoc.gold.gold_dq_summary` ORDER BY fact_table'
```

Every `row_count_diff` should be 0 — every join used to build a fact is on
an already-FK-checked, unique Silver key, so nothing should fan out or
drop rows. A nonzero value here means something's wrong with a join, not
with the source data (already validated in Phases 1–3).

Then spot-check the YTD-vs-prior-year logic against a hand-built fixture
— actually do the arithmetic once by hand rather than trusting the
pipeline blind:

```bash
bq query --use_legacy_sql=false \
  'SELECT * FROM `clientgcpkraftheinzadpoc.gold.gold_ytd_by_year` ORDER BY year'
```

Pick the most recent year's `cutoff_doy` value directly from that
result — **don't assume it equals today's calendar day-of-year.** It's
the latest day-of-year that actually has a `Completed` order in that
year, which can land a day or two earlier than "today" depending on the
generator's last row. Take whatever `cutoff_doy` your latest year
actually shows and run this by-hand check against the raw fact for the
prior year, substituting that same number in place of `<cutoff_doy>`:

```bash
bq query --use_legacy_sql=false \
  "SELECT SUM(line_net_amount_usd) AS revenue_usd, COUNT(DISTINCT order_id) AS order_count
   FROM \`clientgcpkraftheinzadpoc.gold.fct_order_items\`
   WHERE order_status = 'Completed'
     AND EXTRACT(YEAR FROM order_date) = 2025
     AND EXTRACT(DAYOFYEAR FROM order_date) <= <cutoff_doy>"
```

If that number matches the 2025 row in `gold_ytd_by_year`, the YTD logic
is verified, not just assumed. (A mismatch almost always means the cutoff
number used in the by-hand query doesn't match the pipeline's actual
`cutoff_doy` — re-check that first before suspecting the join logic
itself.)

Last, sanity-check one of the curated views renders something plausible:

```bash
bq query --use_legacy_sql=false \
  'SELECT * FROM `clientgcpkraftheinzadpoc.gold.gold_monthly_kpis` ORDER BY year, month'
```

You should see 57 rows (Jan 2022 through Sep 2026), revenue trending up
year over year, December consistently the strongest month, and a
partial, lower number for September 2026 (YTD-only month) — matching the
known seasonality patterns documented in `data_dictionary.md`.

## Report back

Paste (or describe) the `gold_dq_summary` output and whether the YTD
by-hand check matched. If both check out, Phase 4 is done and we move to
Phase 5 (governance layer + the four-role agent architecture, now on
Gemini via Vertex AI).
