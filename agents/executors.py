# Execution-layer abstraction -- orchestrator.py and validation_agent.py
# are handed a "query executor" object with two methods, .validate(sql)
# and .run(sql), and don't need to know how either is actually
# implemented. This is the same abstraction the Databricks build used
# (agents/executors.py there), needed because that platform has two
# genuinely different runtimes: a live-notebook SparkSession (Phase 5)
# vs. a stateless web backend with no attached cluster, talking to a SQL
# Warehouse over an API instead (Phase 6).
#
# GCP simplification worth noting explicitly: BigQuery's client library
# works identically whether it's called from a Cloud Shell script (this
# phase's demo harness) or a stateless Cloud Run backend (Phase 7) -- no
# "live cluster" vs. "warehouse" distinction the way Databricks has. So
# there's only ONE executor here, BigQueryExecutor, reused as-is by both
# this phase's demo script and Phase 7's backend. Nothing analogous to
# Databricks' WarehouseExecutor is needed at all.

from google.cloud import bigquery

from agents import guardrails


class BigQueryExecutor:
    """Wraps a google.cloud.bigquery.Client. Both methods raise the exact
    same guardrails.GuardrailRejected on any rejection (bad SQL, row/
    timeout limit hit, execution error), so validation_agent.py's error
    handling never changes based on where this executor is instantiated."""

    def __init__(self, client: bigquery.Client | None = None, project: str | None = None):
        self.client = client or bigquery.Client(project=project)

    def validate(self, sql_text: str) -> None:
        guardrails.validate(self.client, sql_text)

    def run(self, sql_text: str):
        """Returns (rows, columns). Raises guardrails.GuardrailRejected."""
        return guardrails.execute(self.client, sql_text)
