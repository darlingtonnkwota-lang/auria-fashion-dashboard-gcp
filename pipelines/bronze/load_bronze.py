"""
Bronze loader for the Auria Fashion Group GCP rebuild.

Loads every CSV in ./output/ (produced by generate_data.py) into a BigQuery
`bronze` dataset, one table per CSV, named `bronze_<filename>`.

Mirrors the Databricks Bronze convention documented in the project's
strategy doc:
  - every source column is loaded as STRING (untyped, raw) — no type
    coercion happens in Bronze, that's Silver's job.
  - three provenance columns are appended to every row:
      _source_file        the CSV file name the row came from
      _ingested_at         UTC timestamp of this load run
      _ingestion_batch_id  a UUID shared by every table loaded in this run
  - WRITE_TRUNCATE: each run fully replaces the Bronze tables (Bronze is a
    raw landing zone, not an append log, for this POC).

Usage (from Cloud Shell or any machine with gcloud application-default
credentials and the right BigQuery IAM roles):

    python pipelines/bronze/load_bronze.py --project clientgcpkraftheinzadpoc

Requires: google-cloud-bigquery, pandas (see requirements.txt).
"""

import argparse
import datetime
import glob
import os
import sys
import uuid

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

DATASET_ID = "bronze"
DEFAULT_LOCATION = "US"


def find_csv_dir() -> str:
    """The generator writes CSVs to <repo_root>/output/. Resolve that path
    relative to this script so it works no matter the current working
    directory the script is invoked from."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate = os.path.join(repo_root, "output")
    if os.path.isdir(candidate):
        return candidate
    # fall back to ./output relative to cwd, in case the layout changes
    if os.path.isdir("output"):
        return os.path.abspath("output")
    raise SystemExit(
        f"Couldn't find an output/ directory with CSVs. Looked in:\n"
        f"  {candidate}\n  {os.path.abspath('output')}\n"
        f"Run generate_data.py first."
    )


def ensure_dataset(client: bigquery.Client, project: str, location: str) -> str:
    dataset_ref = f"{project}.{DATASET_ID}"
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {dataset_ref} already exists.")
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)
        print(f"Created dataset {dataset_ref} in {location}.")
    return dataset_ref


def load_one_csv(client: bigquery.Client, dataset_ref: str, csv_path: str, batch_id: str) -> None:
    table_name = os.path.splitext(os.path.basename(csv_path))[0]
    bq_table = f"{dataset_ref}.bronze_{table_name}"

    # Read every column as a plain string — Bronze stays untyped/raw by design.
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=[""])

    ingested_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    df["_source_file"] = os.path.basename(csv_path)
    df["_ingested_at"] = ingested_at
    df["_ingestion_batch_id"] = batch_id

    # Explicit all-STRING schema — don't let autodetect guess types for us.
    schema = [bigquery.SchemaField(col, "STRING") for col in df.columns]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.CSV,
    )

    load_job = client.load_table_from_dataframe(df, bq_table, job_config=job_config)
    load_job.result()  # wait for completion, raises on failure

    table = client.get_table(bq_table)
    print(f"{table_name:24s} {table.num_rows:>8,d} rows  -> {bq_table}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Load Auria CSVs into BigQuery Bronze.")
    parser.add_argument("--project", required=True, help="GCP project ID, e.g. clientgcpkraftheinzadpoc")
    parser.add_argument("--location", default=DEFAULT_LOCATION, help=f"BigQuery dataset location (default: {DEFAULT_LOCATION})")
    args = parser.parse_args()

    csv_dir = find_csv_dir()
    csv_files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
    if not csv_files:
        raise SystemExit(f"No CSVs found in {csv_dir}. Run generate_data.py first.")

    print(f"Found {len(csv_files)} CSVs in {csv_dir}")

    client = bigquery.Client(project=args.project)
    dataset_ref = ensure_dataset(client, args.project, args.location)

    batch_id = str(uuid.uuid4())
    print(f"Ingestion batch id: {batch_id}\n")

    print("--- Loading Bronze tables ---")
    for csv_path in csv_files:
        load_one_csv(client, dataset_ref, csv_path, batch_id)

    print("\nDone. All Bronze tables loaded as STRING columns with provenance metadata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
