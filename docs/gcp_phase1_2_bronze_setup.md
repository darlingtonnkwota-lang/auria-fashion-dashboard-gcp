# GCP Phase 1/2 — Data Generation & BigQuery Bronze Load

Goal: get the same 14-table Auria Fashion Group synthetic dataset used in
the Databricks build into BigQuery, landed exactly the way Bronze landed it
there — untyped (all STRING), one row-for-row copy of the source CSV, plus
three provenance columns. No cleaning, no typing, no dedup — that's Silver's
job (Phase 3).

**Status: ready to run.** `generate_data.py` and
`pipelines/bronze/load_bronze.py` are committed to `dev`. This is a
one-time manual run from Cloud Shell (not wired into Cloud Build) — Bronze
loads aren't part of the CI/CD app-deploy loop from Phase 0, they're a data
pipeline step, run on your own schedule against BigQuery directly.

## What gets loaded

`generate_data.py` is a verbatim port of the same script used for the
Databricks build (seed 42, fully deterministic — same fake data every run).
It writes 14 CSVs to `./output/`:

customers, products, suppliers, stores, warehouses, orders, order_items,
returns, purchase_orders, purchase_order_lines, inventory_movements,
inventory_snapshots, exchange_rates, promotions.

`load_bronze.py` then loads each CSV into a BigQuery dataset called
`bronze`, as a table named `bronze_<csv name>` — e.g. `bronze_customers`,
`bronze_order_items`. Every column is loaded as `STRING`, and three columns
are appended to every row:

- `_source_file` — the CSV file name the row came from
- `_ingested_at` — UTC timestamp of the load run
- `_ingestion_batch_id` — a UUID shared by every table loaded in that run

Each run is `WRITE_TRUNCATE` — Bronze is a raw landing zone for this POC,
not an append log, so re-running the loader replaces the tables cleanly
rather than duplicating rows.

## Run it — Cloud Shell

Open Cloud Shell (console.cloud.google.com, top-right `>_` icon) — it's
already authenticated as you, with your own IAM permissions on the project,
which is all this needs (you don't need to touch the Cloud Build service
account for this step).

```bash
git clone git@github.com:darlingtonnkwota-lang/auria-fashion-dashboard-gcp.git
cd auria-fashion-dashboard-gcp
git checkout dev

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python generate_data.py
python pipelines/bronze/load_bronze.py --project clientgcpkraftheinzadpoc
```

Cloud Shell's git isn't set up with your SSH key by default — if the clone
fails with a permission error, either clone over HTTPS instead
(`https://github.com/darlingtonnkwota-lang/auria-fashion-dashboard-gcp.git`,
since this repo is public, HTTPS clone needs no auth at all for a public
repo) or upload your SSH key into Cloud Shell's home directory. HTTPS clone
is simpler here since you're only pulling, not pushing, from Cloud Shell.

You'll need the BigQuery Data Editor and BigQuery Job User roles on the
project for the load step to succeed — as the project's likely
owner/editor this should already be covered, but if `load_bronze.py` fails
with a permissions error, that's the first thing to check
(IAM & Admin -> IAM in the console).

## Verify

```bash
bq ls bronze
bq query --use_legacy_sql=false \
  'SELECT table_name, row_count FROM `clientgcpkraftheinzadpoc.bronze.__TABLES__`'
```

Or in the console: BigQuery -> clientgcpkraftheinzadpoc -> `bronze` dataset
-> should show 14 tables, each named `bronze_<name>`, with row counts
matching what `generate_data.py` printed when it ran (customers in the
thousands, order_items the largest table, etc.).

## Next

Phase 3 (Silver) reads these Bronze tables, casts types, dedupes, and
normalizes currency — same shape as the Databricks Silver layer, just
BigQuery SQL/views instead of Delta Live Tables notebooks.
