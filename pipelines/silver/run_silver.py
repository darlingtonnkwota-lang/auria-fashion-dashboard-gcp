"""
Silver transform runner for the Auria Fashion Group GCP rebuild.

Runs the SQL scripts in pipelines/silver/sql/ in order against BigQuery,
turning the 14 bronze_* (all-STRING, raw) tables into typed, deduped,
FK-checked, USD-normalized silver_* tables plus a silver_dq_summary
reconciliation table -- the BigQuery equivalent of the Databricks build's
Lakeflow Declarative Pipeline (pipelines/silver/silver_transform.py in
that repo). Same rules, ported to plain SQL since BigQuery has no
DLT-style pipeline framework.

Design decisions carried over from the Databricks build (see that repo's
docs/phase3_silver_setup.md for the full reasoning):
  - Reporting currency is USD. Every local-currency amount gets a sibling
    *_usd column; the original *_local column is kept alongside it.
  - A row that fails a data quality rule is dropped, never silently kept.
    Every rule is a WHERE-clause filter in its own script (the SQL
    equivalent of a named @dlt.expect_or_drop) or a required/nullable FK
    join (the SQL equivalent of a left_semi join).
  - Batch, not streaming -- these are CREATE OR REPLACE TABLE ... AS
    SELECT statements, fully recomputed each run. At this data volume
    (~230K rows total) a full recompute takes seconds.
  - silver_dq_summary is the fast top-level check: Bronze row count vs.
    Silver row count, per table. There's no separate "Data Quality tab"
    the way a Lakeflow pipeline gives you -- if a table's
    dropped_row_count is unexpectedly nonzero, open that table's own
    script in sql/ and check its WHERE filters and FK joins one at a time.

Usage:
    python pipelines/silver/run_silver.py --project clientgcpkraftheinzadpoc
"""

import argparse
import glob
import os
import sys

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

DATASET_ID = "silver"
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
    parser = argparse.ArgumentParser(description="Run the Silver transform against BigQuery.")
    parser.add_argument("--project", required=True, help="GCP project ID, e.g. clientgcpkraftheinzadpoc")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help=f"BigQuery dataset location (default: {DEFAULT_LOCATION})")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)
    ensure_dataset(client, args.project, args.location)

    scripts = sorted(glob.glob(os.path.join(SQL_DIR, "*.sql")))
    if not scripts:
        raise SystemExit(f"No SQL scripts found in {SQL_DIR}")

    print(f"Running {len(scripts)} Silver scripts in order...\n")
    for path in scripts:
        run_script(client, args.project, path)

    print("\nDone. Check silver.silver_dq_summary for the Bronze-to-Silver reconciliation, e.g.:")
    print(
        f"  bq query --use_legacy_sql=false "
        f"'SELECT * FROM `{args.project}.silver.silver_dq_summary` ORDER BY source_table'"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
