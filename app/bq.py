"""
Small BigQuery helper for Phase 7's dashboard endpoints -- deliberately
separate from agents/guardrails.py. The dashboard tiles run fixed,
developer-authored SQL (never user/agent input), so there's nothing for
the guardrail layer to check; they still query through the `authorized`
dataset (never raw `gold`) to keep the same "governed surface" story the
chat sidebar's agent-drafted queries follow, per gcp_strategy.md section 4.

PROJECT/LOCATION are read once at import time from the same env vars
agents/llm_client.py uses, so app/main.py's --set-env-vars at deploy is
the single place both the BigQuery client and the Gemini client get
configured from.
"""

import os

from google.cloud import bigquery

PROJECT = os.environ.get("AURIA_GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
AUTHORIZED_DATASET = "authorized"

_client: bigquery.Client | None = None


def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        if not PROJECT:
            raise RuntimeError(
                "AURIA_GCP_PROJECT (or GOOGLE_CLOUD_PROJECT) is not set -- set it as a "
                "Cloud Run env var (see docs/gcp_phase7_dashboard_frontend_setup.md)."
            )
        _client = bigquery.Client(project=PROJECT)
    return _client


def authorized(table: str) -> str:
    """Fully-qualified `` `project.authorized.table` `` reference."""
    return f"`{PROJECT}.{AUTHORIZED_DATASET}.{table}`"


def query(sql: str, params: list[bigquery.ScalarQueryParameter] | None = None) -> list[dict]:
    """Runs sql (fixed, developer-authored -- never raw user/agent input)
    and returns rows as a list of plain dicts, JSON-serializable as-is."""
    client = get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    rows = client.query(sql, job_config=job_config).result()
    return [dict(row.items()) for row in rows]
