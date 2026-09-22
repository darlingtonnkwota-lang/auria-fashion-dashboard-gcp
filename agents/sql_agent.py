# SQL Agent role: turns a natural-language question (plus any active
# dashboard filters and conversation history) into a single SELECT
# statement against the gold dataset (via the `authorized` views),
# grounded in the version-controlled context layer (context/*.yaml).
# This module only DRAFTS SQL -- it never executes it. See
# validation_agent.py for the execution step, which is the only place a
# query actually touches data.
#
# Ported from the Databricks build's agents/sql_agent.py -- identical
# logic, the only change is the import (llm_client instead of
# claude_client) and the system prompt's platform reference.

import re

from agents import context, llm_client

SYSTEM_PROMPT_TEMPLATE = """You are the SQL Agent for the Auria Fashion Group analytics assistant.

Your only job: given a business question, draft ONE read-only SELECT
statement against the gold dataset (queried through its `authorized`
views) that answers it, using the schema, metric formulas, and rules
below. Write table names UNQUALIFIED (e.g. `dim_product`, not
`project.gold.dim_product`) -- the executor pins the query's default
dataset for you. You never execute SQL yourself -- another agent does
that after checking your query against a guardrail layer, so it is fine
(expected, even) for a bad or out-of-scope draft from you to get
rejected downstream.

Rules:
- Only reference tables/views listed in the Schema section below. Never
  reference bronze or silver tables, and never reference gold_dq_summary.
- Reuse the canonical metric formulas given below rather than inventing
  your own -- they encode business rules (like "Completed orders only")
  that are easy to get subtly wrong from scratch.
- If the question is genuinely ambiguous (e.g. "top products" -- by revenue
  or units?), pick the most common-sense interpretation, draft SQL for it,
  and say what you assumed in your rationale. Never silently guess without
  disclosing the assumption.
- If you are able to call the propose_sql tool, call it exactly once with
  your finished SQL and a short rationale, and do not also answer in plain
  text. If no tool is available to you, instead answer with your SQL in a
  ```sql fenced code block, followed by a short paragraph with your
  rationale.

{context_block}
"""

PROPOSE_SQL_TOOL = {
    "type": "function",
    "name": "propose_sql",
    "description": "Submit the single SELECT statement that answers the question.",
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "One SELECT statement. No trailing semicolon needed.",
            },
            "rationale": {
                "type": "string",
                "description": (
                    "1-3 sentences: which tables/metrics you used, and any "
                    "assumption you made about an ambiguous question."
                ),
            },
        },
        "required": ["sql", "rationale"],
    },
}

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_RATIONALE_FALLBACK = "(tool-calling unavailable or unused; SQL extracted from a code block)"


def draft_sql(question: str, filters: dict | None = None, history: list | None = None) -> dict:
    """Returns {"sql": ..., "rationale": ...}."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context_block=context.build_sql_agent_context()
    )

    user_content = question
    if filters:
        user_content += (
            "\n\nActive dashboard filters (apply these as additional WHERE "
            f"conditions): {filters}"
        )

    input_items = list(history) if history else []
    input_items.append(llm_client.text_input("user", user_content))

    # Same defensive fallback as the Databricks build: try tool-calling
    # first, and if the model/endpoint rejects the `tools` param for any
    # reason, fall back to a prompt-only request and parse a fenced SQL
    # block out of the plain-text answer instead of crashing the whole
    # pipeline over an API-shape mismatch.
    try:
        response = llm_client.respond(
            input_items,
            instructions=system_prompt,
            tools=[PROPOSE_SQL_TOOL],
            tool_choice="auto",
            max_output_tokens=1500,
        )
        call = llm_client.extract_function_call(response, name="propose_sql")
        if call:
            _, args = call
            return {"sql": args["sql"].strip(), "rationale": args.get("rationale", "").strip()}
        content = llm_client.extract_text(response)
    except Exception:  # noqa: BLE001 -- deliberately broad: any tool-calling failure falls back
        response = llm_client.respond(
            input_items, instructions=system_prompt, max_output_tokens=1500
        )
        content = llm_client.extract_text(response)

    match = _SQL_FENCE_RE.search(content)
    if match:
        return {"sql": match.group(1).strip(), "rationale": _RATIONALE_FALLBACK}

    raise ValueError(f"SQL agent did not produce a usable query. Raw response: {content}")
