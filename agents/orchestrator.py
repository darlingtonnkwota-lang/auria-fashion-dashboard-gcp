# Orchestrator: the single entry point the demo script (this phase) or
# the frontend backend (Phase 7) calls. Owns conversation state and
# dashboard filters, and runs the SQL Agent -> Validation/Execution
# Agent -> Insight Agent pipeline for one question.
#
# These are logical roles inside one small application, not four
# separate services (gcp_strategy.md section 2) -- but each role is
# still its own module with a single responsibility, so the boundary is
# real in the code even though it isn't a network boundary.
#
# Ported unchanged from the Databricks build's agents/orchestrator.py --
# executor-agnostic, so it needed zero changes for the GCP port.
# `executor` is a BigQueryExecutor (agents/executors.py); this module
# never touches BigQuery directly.

from agents import insight_agent, sql_agent, validation_agent


def answer_question(
    executor, question: str, filters: dict | None = None, history: list | None = None
) -> dict:
    """Runs the full 4-role pipeline for one question.

    Returns a dict with everything a caller needs to render the answer:
    the drafted SQL and rationale, whether it was rejected (and why), the
    raw result rows/columns (for a table or chart), and the final
    natural-language answer.
    """
    draft = sql_agent.draft_sql(question, filters=filters, history=history)
    execution_result = validation_agent.execute_sql(executor, draft["sql"])
    insight = insight_agent.explain(
        question, draft["sql"], draft["rationale"], execution_result
    )

    return {
        "question": question,
        "filters": filters or {},
        "sql": draft["sql"],
        "sql_rationale": draft["rationale"],
        "rejected": not execution_result["ok"],
        "rejection_reason": execution_result.get("error"),
        "rows": execution_result.get("rows", []),
        "columns": execution_result.get("columns", []),
        "answer": insight["answer"],
    }
