# SQL Agent role: turns a natural-language question (plus any active
# dashboard filters and conversation history) into a single SELECT
# statement against the gold dataset (via the `authorized` views),
# grounded in the version-controlled context layer (context/*.yaml).
# This module only DRAFTS SQL -- it never executes it. See
# validation_agent.py for the execution step, which is the only place a
# query actually touches data.
#
# Ported from the Databricks build's agents/sql_agent.py -- the prompt,
# tool schema, and fenced-code fallback are unchanged. Two GCP-specific
# additions beyond the import swap (llm_client instead of claude_client):
# a forced tool_choice (see _one_attempt) so Gemini can't opt out of
# drafting SQL, and one internal retry before giving up (see draft_sql).

import re
import sys
from datetime import date

from agents import context, llm_client

SYSTEM_PROMPT_TEMPLATE = """You are the SQL Agent for the Auria Fashion Group analytics assistant.

Today's date is {today}. The gold dataset's history runs up to roughly
this date -- a quarter or month at or before today is historical data
you can query, not a future period. Never refuse a question by
assuming a date is "in the future" without checking it against
today's date first.

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
- If part of the question can't be determined from the schema below (e.g.
  it asks about an attribute that isn't tracked, or a causal link the data
  can't establish), do NOT refuse and do NOT submit an empty or placeholder
  SQL statement. Instead, draft the best SQL you can for the part that IS
  answerable, and use the rationale to name exactly what could not be
  determined and why. A partial, honestly-caveated answer is always the
  right move -- an empty submission is never acceptable.
- You must call the propose_sql tool exactly once, every time, with a
  non-empty `sql` value -- this is required, not optional, regardless of
  how confident you are in the answer. Do not also answer in plain text.
  (If the propose_sql tool is genuinely unavailable to you for some
  reason, answer instead with your SQL in a ```sql fenced code block
  followed by a short paragraph with your rationale -- but this should
  not happen in normal operation.)

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


def _one_attempt(input_items: list, system_prompt: str) -> dict | None:
    """One draft attempt. Returns {"sql", "rationale"} or None if this
    attempt didn't yield a usable query (caller decides whether to retry)."""
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
            # "required" (Gemini's ANY mode), not "auto": with auto, Gemini
            # sometimes opts out of calling propose_sql entirely and answers
            # in plain prose instead of drafting best-effort SQL.
            tool_choice="required",
            # 8192, not 1500: confirmed root cause of the empty-response
            # failures on the harder demo questions -- Gemini 2.5 Flash's
            # internal "thinking" tokens count against max_output_tokens,
            # and on Vertex AI, thinking_budget=0 is unreliably honored
            # once `tools` is present (a known SDK/API limitation, not
            # something client code can reliably work around), so a low
            # ceiling here just means thinking silently eats the whole
            # budget before the model ever emits the function call. A
            # generous ceiling is the safety net.
            max_output_tokens=8192,
        )
        call = llm_client.extract_function_call(response, name="propose_sql")
        if call:
            _, args = call
            sql = (args.get("sql") or "").strip()
            if sql:
                return {"sql": sql, "rationale": (args.get("rationale") or "").strip()}
        content = llm_client.extract_text(response)
        if not content:
            print(
                f"[sql_agent] tool-forced call produced no usable SQL and no text -- "
                f"{llm_client.debug_describe(response)}",
                file=sys.stderr,
            )
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: any tool-calling failure falls back
        print(f"[sql_agent] tool-forced call raised {exc!r}, falling back", file=sys.stderr)
        try:
            response = llm_client.respond(
                input_items, instructions=system_prompt, max_output_tokens=8192
            )
            content = llm_client.extract_text(response)
        except Exception:  # noqa: BLE001 -- both attempts failed; let the caller retry
            return None

    match = _SQL_FENCE_RE.search(content)
    if match:
        return {"sql": match.group(1).strip(), "rationale": _RATIONALE_FALLBACK}
    return None


def draft_sql(question: str, filters: dict | None = None, history: list | None = None) -> dict:
    """Returns {"sql": ..., "rationale": ...}.

    Occasionally an LLM call comes back with neither a tool call nor any
    text at all (a transient generation quirk, not a code bug) -- worth
    one retry before giving up, since retrying resolves it most of the
    time. Raises ValueError only if every attempt fails; orchestrator.py
    catches that and turns it into a disclosed rejection instead of
    crashing the whole pipeline."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        today=date.today().isoformat(),
        context_block=context.build_sql_agent_context(),
    )

    user_content = question
    if filters:
        user_content += (
            "\n\nActive dashboard filters (apply these as additional WHERE "
            f"conditions): {filters}"
        )

    input_items = list(history) if history else []
    input_items.append(llm_client.text_input("user", user_content))

    attempts = 2
    for attempt in range(attempts):
        result = _one_attempt(input_items, system_prompt)
        if result:
            return result

    raise ValueError(
        f"SQL agent did not produce a usable query after {attempts} attempt(s) "
        f"for question: {question!r}"
    )
