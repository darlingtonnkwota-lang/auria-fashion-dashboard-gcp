"""
Governance runner for the Auria Fashion Group GCP rebuild.

Runs the SQL scripts in pipelines/governance/sql/ in order against
BigQuery: creates the `authorized` dataset and its 18 authorized views
over `gold`, and the `validate_gold_sql` governed validation function in
`gold`. This is the BigQuery half of Phase 5's governance layer -- the
other half (IAM: scoping a dedicated service account to SELECT on
`authorized` only) is a one-time console/gcloud step documented in
docs/gcp_phase5_governance_agents_setup.md, not something this script
does (this POC runs under your own gcloud identity throughout, matching
the Databricks build's own documented simplification).

Usage:
    python pipelines/governance/run_governance.py --project clientgcpkraftheinzadpoc
"""

import argparse
import glob
import os
import sys

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

DATASET_ID = "authorized"
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
    parser = argparse.ArgumentParser(description="Run the governance layer setup against BigQuery.")
    parser.add_argument("--project", required=True, help="GCP project ID, e.g. clientgcpkraftheinzadpoc")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help=f"BigQuery dataset location (default: {DEFAULT_LOCATION})")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)
    ensure_dataset(client, args.project, args.location)

    scripts = sorted(glob.glob(os.path.join(SQL_DIR, "*.sql")))
    if not scripts:
        raise SystemExit(f"No SQL scripts found in {SQL_DIR}")

    print(f"Running {len(scripts)} governance scripts in order...\n")
    for path in scripts:
        run_script(client, args.project, path)

    print("\nDone. Sanity-check the validation function, e.g.:")
    print(
        f"  bq query --use_legacy_sql=false "
        f"\"SELECT \\`{args.project}.gold.validate_gold_sql\\`('SELECT 1')\""
    )
    print("Should print OK. See docs/gcp_phase5_governance_agents_setup.md for the full sanity-check list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
