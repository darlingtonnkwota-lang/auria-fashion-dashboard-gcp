"""
FastAPI backend for Phase 7 -- the real backend the walking-skeleton
app/main.py's own header comment said this would become once Phase 5's
agent code landed. Two jobs:

1. POST /api/ask -- wraps agents.orchestrator's 4-role pipeline (Gemini
   via Vertex AI, unchanged from Phase 5) behind one HTTP endpoint, using
   agents.executors.BigQueryExecutor. Same request/response contract the
   Databricks build's backend/main.py used, so the frontend's chat
   sidebar logic ported over almost unchanged.
2. GET /api/dashboard/* -- Phase 7's actual new surface: a native,
   in-app dashboard (no Looker Studio iframe -- see gcp_strategy.md
   section 7's revised decision) means the frontend needs real
   aggregated data to draw its own charts, not a report URL. Each of
   these queries a fixed, developer-authored SQL statement (see app/bq.py)
   against the `authorized` dataset -- the same governed surface the
   chat sidebar's agent-drafted queries go through, just without needing
   the guardrail layer (this SQL never comes from user or model input).

No CORS middleware: the frontend calls these through its own same-origin
Next.js Route Handlers (frontend/app/api/**/route.ts), which proxy to
this service's URL server-side using a runtime-only env var
(BACKEND_URL) -- never exposed to the browser. See
docs/gcp_phase7_dashboard_frontend_setup.md.
"""

import os
from datetime import date

from fastapi import FastAPI, HTTPException
from google.cloud import bigquery
from pydantic import BaseModel

from agents import orchestrator
from agents.executors import BigQueryExecutor

from bq import authorized, query

app = FastAPI(title="Auria Fashion Group — GCP backend")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "auria-backend"}


@app.get("/")
def root():
    return {"message": "Auria Fashion Group GCP backend"}


# ---------------------------------------------------------------------------
# 1. Chat sidebar -- the Phase 5 agent pipeline, over HTTP.
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str
    filters: dict | None = None
    # Same Phase 6-parity MVP simplification the Databricks build named:
    # sql_agent.draft_sql accepts a `history` list, but nothing here
    # populates it from earlier turns yet -- each question is answered
    # independently. A natural next-round enhancement, not an oversight.
    history: list | None = None


@app.post("/api/ask")
def ask(payload: AskRequest):
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        executor = BigQueryExecutor(project=os.environ.get("AURIA_GCP_PROJECT"))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500, detail=f"Backend misconfigured: {exc}"
        ) from exc

    return orchestrator.answer_question(
        executor, payload.question, filters=payload.filters, history=payload.history
    )


# ---------------------------------------------------------------------------
# 2. Native dashboard tiles.
# ---------------------------------------------------------------------------

@app.get("/api/dashboard/monthly-kpis")
def monthly_kpis():
    sql = f"""
        SELECT year, month, revenue_usd, order_count, aov_usd, units_sold,
               margin_usd, margin_pct, returns_usd, return_count, return_rate_pct
        FROM {authorized('gold_monthly_kpis')}
        ORDER BY year, month
    """
    return query(sql)


@app.get("/api/dashboard/ytd")
def ytd():
    sql = f"""
        SELECT year, cutoff_doy, revenue_usd, order_count, aov_usd, margin_usd
        FROM {authorized('gold_ytd_by_year')}
        ORDER BY year
    """
    return query(sql)


@app.get("/api/dashboard/forecast")
def forecast():
    sql = f"""
        SELECT metric, month_date, value, lower_bound, upper_bound, is_forecast
        FROM {authorized('gold_sales_forecast')}
        ORDER BY metric, month_date
    """
    return query(sql)


@app.get("/api/dashboard/top-products")
def top_products(year: int | None = None, limit: int = 5):
    year = year or date.today().year
    sql = f"""
        SELECT p.product_id, p.product_name, p.category, p.sub_category,
               SUM(t.revenue_usd) AS revenue_usd, SUM(t.units_sold) AS units_sold,
               SUM(t.margin_usd) AS margin_usd
        FROM {authorized('gold_top_products_monthly')} t
        JOIN {authorized('dim_product')} p ON p.product_id = t.product_id
        WHERE t.year = @year
        GROUP BY p.product_id, p.product_name, p.category, p.sub_category
        ORDER BY revenue_usd DESC
        LIMIT @limit
    """
    params = [
        bigquery.ScalarQueryParameter("year", "INT64", year),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]
    return query(sql, params)


@app.get("/api/dashboard/top-customers")
def top_customers(limit: int = 10):
    # Lifetime value, all time, no date filter -- see
    # context/metric_specs.yaml's lifetime_value_usd. Deliberately not
    # year-scoped, unlike top-products: "lifetime" means lifetime.
    sql = f"""
        SELECT c.customer_id, c.first_name, c.last_name, c.region,
               SUM(f.line_net_amount_usd) AS lifetime_value_usd,
               COUNT(DISTINCT f.order_id) AS order_count
        FROM {authorized('fct_order_items')} f
        JOIN {authorized('dim_customer')} c ON c.customer_id = f.customer_id
        WHERE f.order_status = 'Completed'
        GROUP BY c.customer_id, c.first_name, c.last_name, c.region
        ORDER BY lifetime_value_usd DESC
        LIMIT @limit
    """
    params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    return query(sql, params)


@app.get("/api/dashboard/returns-by-product")
def returns_by_product(year: int | None = None, limit: int = 5):
    year = year or date.today().year
    sql = f"""
        SELECT p.product_id, p.product_name, p.category, p.size_range,
               SUM(t.return_count) AS return_count, SUM(t.lines_sold) AS lines_sold,
               SAFE_DIVIDE(SUM(t.return_count), SUM(t.lines_sold)) * 100 AS return_rate_pct
        FROM {authorized('gold_returns_by_product_monthly')} t
        JOIN {authorized('dim_product')} p ON p.product_id = t.product_id
        WHERE t.year = @year
        GROUP BY p.product_id, p.product_name, p.category, p.size_range
        HAVING lines_sold > 0
        ORDER BY return_rate_pct DESC
        LIMIT @limit
    """
    params = [
        bigquery.ScalarQueryParameter("year", "INT64", year),
        bigquery.ScalarQueryParameter("limit", "INT64", limit),
    ]
    return query(sql, params)


@app.get("/api/dashboard/channel-performance")
def channel_performance():
    sql = f"""
        SELECT year, channel, SUM(revenue_usd) AS revenue_usd,
               SUM(order_count) AS order_count
        FROM {authorized('gold_channel_performance')}
        GROUP BY year, channel
        ORDER BY year, channel
    """
    return query(sql)


@app.get("/api/dashboard/supplier-performance")
def supplier_performance():
    sql = f"""
        SELECT supplier_id, supplier_name, po_count, avg_actual_lead_time_days,
               pct_late, stated_avg_lead_time_days, reliability_score
        FROM {authorized('gold_supplier_performance')}
        ORDER BY avg_actual_lead_time_days DESC
    """
    return query(sql)


@app.get("/api/dashboard/product-performance")
def product_performance():
    # Diagnostic view, not a leaderboard: one row per product, all-time,
    # so a scatter/bubble chart can show volume (lines_sold) against
    # return_rate_pct with revenue_usd sizing each bubble -- the products
    # worth worrying about are the ones that are both high-volume AND
    # high-return, which a top-5-by-return-rate table (see
    # returns_by_product above) can't show on its own: a niche product
    # with a 40% return rate on 10 units matters far less than a
    # bestseller with a 12% return rate on 3,000 units.
    #
    # gold_returns_by_product_monthly and gold_top_products_monthly are
    # both monthly grain, so each is aggregated to an all-time total per
    # product before joining -- same "sum first, then divide" pattern
    # metric_specs.yaml requires for return_rate_pct (never average a
    # per-month rate across months, that would weight a slow month and a
    # busy month equally).
    sql = f"""
        WITH returns_agg AS (
            SELECT product_id,
                   SUM(lines_sold) AS lines_sold,
                   SUM(return_count) AS return_count,
                   SAFE_DIVIDE(SUM(return_count), SUM(lines_sold)) * 100 AS return_rate_pct
            FROM {authorized('gold_returns_by_product_monthly')}
            GROUP BY product_id
        ),
        revenue_agg AS (
            SELECT product_id, SUM(revenue_usd) AS revenue_usd
            FROM {authorized('gold_top_products_monthly')}
            GROUP BY product_id
        )
        SELECT p.product_id, p.product_name, p.category,
               r.lines_sold, r.return_rate_pct,
               COALESCE(v.revenue_usd, 0) AS revenue_usd
        FROM returns_agg r
        JOIN {authorized('dim_product')} p ON p.product_id = r.product_id
        LEFT JOIN revenue_agg v ON v.product_id = r.product_id
        WHERE r.lines_sold > 0
        ORDER BY r.lines_sold DESC
    """
    return query(sql)
