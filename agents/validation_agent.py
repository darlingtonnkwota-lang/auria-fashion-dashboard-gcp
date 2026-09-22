# Validation/Execution Agent role: takes the SQL Agent's drafted query and
# runs it through the guardrail layer via the executor the caller is
# using -- agents/executors.py's BigQueryExecutor. The actual checks are
# agents/guardrails.py's: the BigQuery validate_gold_sql function, plus
# the row-limit/timeout wrapper.
#
# This module has no LLM call in it at all. That's the point of this
# role: it is deterministic code, not a model that could be talked into
# skipping a check.
#
# Ported unchanged from the Databricks build's agents/validation_agent.py
# -- executor-agnostic, so it needed zero changes for the GCP port.

from agents import guardrails


def execute_sql(executor, sql: str) -> dict:
    """Returns either
        {"ok": True, "rows": [...], "columns": [...]}
    or
        {"ok": False, "error": "..."}
    -- never raises, so the orchestrator can always hand the result to the
    insight agent to explain, including a rejection."""
    try:
        rows, columns = executor.run(sql)
        return {"ok": True, "rows": rows, "columns": columns}
    except guardrails.GuardrailRejected as exc:
        return {"ok": False, "error": str(exc)}
