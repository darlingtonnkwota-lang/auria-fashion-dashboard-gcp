# Insight/Viz Agent role: takes the original question, the SQL that was
# run (or the guardrail rejection reason), and the result rows, and
# produces the final natural-language answer -- always disclosing the SQL
# used (or why nothing ran) and suggesting a chart/table format for the
# frontend.
#
# Ported from the Databricks build's agents/insight_agent.py -- identical
# logic, the only change is the import (llm_client instead of
# claude_client).

import json

from agents import context, llm_client

SYSTEM_PROMPT_TEMPLATE = """You are the Insight Agent for the Auria Fashion Group analytics assistant.
You write the final answer a business user actually reads.

Rules:
- Never state a number that isn't present in the query results you were given.
- Always disclose the SQL that was run. If the query was rejected by the
  guardrail layer instead, say plainly that it was rejected and why --
  never invent an answer to paper over a rejected query.
- Mention a caveat from the glossary below only when it actually applies to
  this specific answer (e.g. the current-cost margin caveat, or the YTD
  cutoff not being today's calendar date) -- not as boilerplate on every
  answer.
- Suggest whether the result is best shown as a single number, a table, or
  a chart (and which chart type), for the frontend to render.

{context_block}
"""


def explain(question: str, sql: str, rationale: str, execution_result: dict) -> dict:
    """Returns {"answer": str, "sql_disclosed": str, "was_rejected": bool}."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context_block=context.build_insight_agent_context()
    )

    if execution_result["ok"]:
        result_block = {
            "columns": execution_result["columns"],
            # Keep the prompt small -- the full row set is already available
            # to the frontend directly from the orchestrator's return value,
            # the insight agent just needs enough to describe it accurately.
            "rows": execution_result["rows"][:50],
            "row_count_returned": len(execution_result["rows"]),
        }
        user_content = (
            f"Question: {question}\n\n"
            f"SQL agent's rationale: {rationale}\n\n"
            f"SQL that was run:\n{sql}\n\n"
            f"Results (JSON):\n{json.dumps(result_block, default=str)}"
        )
    else:
        user_content = (
            f"Question: {question}\n\n"
            f"SQL agent's rationale: {rationale}\n\n"
            f"SQL that was drafted:\n{sql}\n\n"
            f"This query was REJECTED by the guardrail layer before it ran. "
            f"Reason: {execution_result['error']}\n\n"
            "Explain to the user that this can't be answered as asked, and why, "
            "without fabricating a result."
        )

    response = llm_client.respond(
        [llm_client.text_input("user", user_content)],
        instructions=system_prompt,
        max_output_tokens=800,
    )
    answer = llm_client.extract_text(response)

    return {
        "answer": answer.strip(),
        "sql_disclosed": sql,
        "was_rejected": not execution_result["ok"],
    }
