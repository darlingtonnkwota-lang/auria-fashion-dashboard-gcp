"""
Gold transform runner for the Auria Fashion Group GCP rebuild.

Runs the SQL scripts in pipelines/gold/sql/ in order against BigQuery,
turning the 14 silver_* tables into a star schema (7 dim_* dimensions,
4 fct_* facts) plus 7 curated gold_* reporting views and a
gold_dq_summary reconciliation table -- the BigQuery equivalent of the
Databricks build's Lakeflow Declarative Pipeline
(pipelines/gold/gold_transform.py in that repo). Same rules, ported to
plain SQL.

Design decisions carried over from the Databricks build (see that repo's
docs/phase4_gold_setup.md for the full reasoning):
  - Natural keys, not surrogate keys -- every dimension is keyed by its
    already-unique Silver id.
  - Cancelled orders stay in fct_order_items, filtered out in every
    curated gold_* view (order_status = 'Completed').
  - Returns are their own fact (fct_returns), never netted into
    fct_order_items.
  - Aggregate views are keyed by id only (e.g. product_id, not
    product_name) -- join to the matching dim_* for anything descriptive.
  - Revenue attributes to the customer's home region, not the store's.
  - gold_ytd_by_year cuts every year off at the same day-of-year (the
    latest day-of-year actually present in the most recent year), so a
    partial current year compares fairly against prior full years.
  - KNOWN LIMITATION: fct_order_items.line_cogs_usd uses each product's
    CURRENT unit_cost_usd, not a cost-as-of-order-date history (Silver/
    Bronze don't carry one). Not worth a real cost-history table for
    this demo dataset, where costs don't change during the generated
    window anyway.

Usage:
    python pipelines/gold/run_gold.py --project clientgcpkraftheinzadpoc
"""

import argparse
import glob
import os
import sys

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

DATASET_ID = "gold"
DEFAULT_LOCATION = "US"
SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")


def ensure_dataset(client: bigquery.Client, project: str, location: str) -> None:
    dataset_ref = f"{project}.{DATASET_ID}"
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_ref} already exists.")
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)
        print(f"Created dataset {dataset_ref} in {location}.")


def run_script(client: bigquery.Client, project: str, path: str) -> None:
    with open(path) as f:
        sql = f.read()
    sql = sql.replace("__PROJECT__", project)
    job = client.query(sql)
    job.result()  # wait for completion, raises on failure
    print(f"OK  {os.path.basename(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Gold transform against BigQuery.")
    parser.add_argument("--project", required=True, help="GCP project ID, e.g. clientgcpkraftheinzadpoc")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help=f"BigQuery dataset location (default: {DEFAULT_LOCATION})")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)
    ensure_dataset(client, args.project, args.location)

    scripts = sorted(glob.glob(os.path.join(SQL_DIR, "*.sql")))
    if not scripts:
        raise SystemExit(f"No SQL scripts found in {SQL_DIR}")

    print(f"Running {len(scripts)} Gold scripts in order...\n")
    for path in scripts:
        run_script(client, args.project, path)

    print("\nDone. This produces 19 tables under the gold dataset: 7 dim_*, "
          "4 fct_*, 7 curated gold_* views, plus gold_dq_summary.")
    print("Check the reconciliation, e.g.:")
    print(
        f"  bq query --use_legacy_sql=false "
        f"'SELECT * FROM `{args.project}.gold.gold_dq_summary` ORDER BY fact_table'"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
