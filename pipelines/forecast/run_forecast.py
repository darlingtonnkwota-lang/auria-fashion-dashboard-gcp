"""
Forecast runner for the Auria Fashion Group GCP rebuild -- Phase 6.

Builds gold_sales_forecast the BigQuery ML way: two trained ARIMA_PLUS
models (revenue, order_count), a 6-month-ahead ML.FORECAST call for
each, unioned with history into one table -- the direct analogue of the
Databricks build's ml/forecast_training.py Prophet notebook, per
gcp_strategy.md section 6. See pipelines/forecast/sql/*.sql for the SQL
itself; this script just runs it in order and prints real numbers,
including a genuine (if simplified) holdout backtest -- not just "it
ran without an error."

Usage:
    python pipelines/forecast/run_forecast.py --project clientgcpkraftheinzadpoc
"""

import argparse
import datetime
import os
import sys

from google.cloud import bigquery

SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")
HOLDOUT_MONTHS = 6


def _read_sql(name: str) -> str:
    with open(os.path.join(SQL_DIR, name)) as f:
        return f.read()


def run_ddl(client: bigquery.Client, project: str, name: str) -> None:
    sql = _read_sql(name).replace("__PROJECT__", project)
    job = client.query(sql)
    job.result()  # wait for completion, raises on failure
    print(f"OK  {name}")


def compute_holdout_cutoff(client: bigquery.Client, project: str) -> str:
    """Last complete month minus (HOLDOUT_MONTHS - 1), as 'YYYY-MM-01' --
    the first month held OUT of backtest training, so the backtest
    model's forecast covers exactly the last HOLDOUT_MONTHS complete
    months, which already have real actuals to compare against."""
    sql = f"""
        SELECT MAX(DATE(year, month, 1)) AS max_complete_month
        FROM `{project}.gold.gold_monthly_kpis`
        WHERE NOT (
          year = EXTRACT(YEAR FROM CURRENT_DATE())
          AND month = EXTRACT(MONTH FROM CURRENT_DATE())
        )
    """
    rows = list(client.query(sql).result())
    max_complete_month = rows[0]["max_complete_month"]
    if max_complete_month is None:
        raise SystemExit("gold_monthly_kpis has no complete months -- run Phase 4 first.")
    # First day of the month HOLDOUT_MONTHS-1 months before the last
    # complete month, e.g. last complete = 2026-08-01, HOLDOUT_MONTHS=6
    # -> cutoff = 2026-03-01, holding out Mar-Aug (6 months) inclusive.
    year, month = max_complete_month.year, max_complete_month.month
    total_months = year * 12 + (month - 1) - (HOLDOUT_MONTHS - 1)
    cutoff_year, cutoff_month = divmod(total_months, 12)
    cutoff_month += 1
    cutoff = datetime.date(cutoff_year, cutoff_month, 1)
    print(f"Last complete month in gold_monthly_kpis: {max_complete_month}")
    print(f"Backtest holdout cutoff (train < this date, test >= this date): {cutoff}\n")
    return cutoff.isoformat()


def run_backtest(client: bigquery.Client, project: str, holdout_cutoff: str) -> None:
    for name in ("04_backtest_model_revenue.sql", "05_backtest_model_orders.sql"):
        sql = (
            _read_sql(name)
            .replace("__PROJECT__", project)
            .replace("__HOLDOUT_CUTOFF__", holdout_cutoff)
        )
        job = client.query(sql)
        job.result()
        print(f"OK  {name}")

    sql = (
        _read_sql("06_backtest_report.sql")
        .replace("__PROJECT__", project)
        .replace("__HOLDOUT_CUTOFF__", holdout_cutoff)
    )
    rows = list(client.query(sql).result())
    print("\nBacktest accuracy (last 6 known complete months, held out of training):")
    print(f"{'metric':<14}{'holdout_months':<16}{'mape_pct':<12}{'rmse':<16}{'mae':<16}")
    for row in rows:
        print(
            f"{row['metric']:<14}{row['holdout_months']:<16}{row['mape_pct']:<12}"
            f"{row['rmse']:<16}{row['mae']:<16}"
        )
    print(
        "\nRead this in context, not as a lab result: one holdout window (not "
        "Prophet's multiple rolling cutoffs), against ~4.7 years of monthly "
        "history -- enough to catch a model that's badly wrong, not a tight "
        "confidence interval on the error itself."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 6 sales forecast against BigQuery.")
    parser.add_argument("--project", required=True, help="GCP project ID, e.g. clientgcpkraftheinzadpoc")
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="Skip the holdout backtest (04-06) and only build the production forecast (01-03).",
    )
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)

    print("### 1. Train the two production forecast models and build gold_sales_forecast\n")
    run_ddl(client, args.project, "01_model_forecast_revenue.sql")
    run_ddl(client, args.project, "02_model_forecast_orders.sql")
    run_ddl(client, args.project, "03_gold_sales_forecast.sql")

    row_count = list(
        client.query(
            f"SELECT COUNT(*) AS n FROM `{args.project}.gold.gold_sales_forecast`"
        ).result()
    )[0]["n"]
    print(f"\ngold_sales_forecast row count: {row_count} (expect 2 metrics x "
          f"(complete months of history + 6 forecast months))")

    if args.skip_backtest:
        print("\n--skip-backtest passed -- skipping steps 04-06.")
        return 0

    print("\n### 2. Holdout backtest (how good is this model, really?)\n")
    holdout_cutoff = compute_holdout_cutoff(client, args.project)
    run_backtest(client, args.project, holdout_cutoff)

    print("\n### 3. Report back")
    print(
        "Paste (or describe): the gold_sales_forecast row count above, the "
        "backtest table, and whether "
        "`SELECT * FROM gold.gold_sales_forecast WHERE is_forecast = true ORDER BY metric, month_date` "
        "shows lower_bound < value < upper_bound on every forecast row."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
