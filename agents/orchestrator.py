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
# Ported from the Databricks build's agents/orchestrator.py --
# executor-agnostic, so the pipeline shape needed zero changes for the
# GCP port. The one addition (not in the Databricks version): a
# try/except around sql_agent.draft_sql so a still-failing LLM draft
# degrades into a disclosed rejection instead of crashing the whole
# batch -- see the docstring below for why.
# `executor` is a BigQueryExecutor (agents/executors.py); this module
# never touches BigQuery directly.

from agents import guardrails, insight_agent, sql_agent, validation_agent


def answer_question(
    executor, question: str, filters: dict | None = None, history: list | None = None
) -> dict:
    """Runs the full 4-role pipeline for one question.

    Returns a dict with everything a caller needs to render the answer:
    the drafted SQL and rationale, whether it was rejected (and why), the
    raw result rows/columns (for a table or chart), and the final
    natural-language answer.

    Every downstream step (validation_agent.execute_sql, guardrails.*) is
    already designed to never raise -- a bad or out-of-scope query comes
    back as a disclosed rejection, not a crash. sql_agent.draft_sql is the
    one exception: it can still raise if the LLM call itself never
    produces a usable query (it retries once internally first). Catching
    that here keeps the same "always disclose, never crash" contract end
    to end, instead of letting one bad draft take down a whole batch of
    questions.
    """
    # Governance demo addition: a restricted-topic question (SIN, phone
    # number, home address, date of birth, etc. -- see
    # guardrails.check_restricted_topic) is rejected right here, before
    # the SQL agent or BigQuery are touched at all. It's deterministic
    # and instant on purpose -- the rejection can't depend on the LLM
    # happening to recognize the request as out of scope, and it must
    # never be phrased as "couldn't find it" (see that function's
    # docstring for why).
    restricted_reason = guardrails.check_restricted_topic(question)
    if restricted_reason:
        return {
            "question": question,
            "filters": filters or {},
            "sql": "",
            "sql_rationale": "(no SQL drafted -- rejected before reaching the SQL agent)",
            "rejected": True,
            "rejection_reason": restricted_reason,
            "rows": [],
            "columns": [],
            "answer": restricted_reason,
        }

    try:
        draft = sql_agent.draft_sql(question, filters=filters, history=history)
    except Exception as exc:  # noqa: BLE001 -- surfaced as a disclosed rejection, not a crash
        execution_result = {"ok": False, "error": f"SQL agent failed to draft a query: {exc}"}
        insight = insight_agent.explain(question, "", "(no SQL drafted)", execution_result)
        return {
            "question": question,
            "filters": filters or {},
            "sql": "",
            "sql_rationale": "(no SQL drafted)",
            "rejected": True,
            "rejection_reason": execution_result["error"],
            "rows": [],
            "columns": [],
            "answer": insight["answer"],
        }

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
