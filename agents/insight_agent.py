# Insight/Viz Agent role: takes the original question, the SQL that was
# run (or the guardrail rejection reason), and the result rows, and
# produces the final natural-language answer.
#
# Originally ported from the Databricks build's agents/insight_agent.py
# with just an import swap (llm_client instead of claude_client). Prompt
# rewritten after live feedback from a business-user test of the
# frontend's chat sidebar: the old prompt's "always disclose the SQL"
# and "suggest a table/chart format" rules were being followed by
# pasting a raw SQL code block and a markdown table straight into the
# answer text -- which is redundant with what the frontend already
# renders next to that answer (ChatSidebar.tsx's `<ResultTable>` shows
# the real result rows as an actual formatted table, and a separate
# collapsible "SQL used" panel already discloses the exact SQL). The
# "suggest a format" instruction was never wired to anything on the
# frontend side either -- it always renders the real table regardless
# of what this agent says -- so business users were seeing a wall of
# SQL and a duplicate ASCII-ish table above the real, nicely-formatted
# one. This agent's only job now is the plain-English narrative that
# goes with those two things, not a restatement of either.
#
# Second round of feedback, after the SQL/table fix landed: the fix
# traded too far toward terse -- a flat 2-5 sentence single paragraph
# read as "one mushed up paragraph" and too high-level for diagnostic
# questions (e.g. "why is the return rate high for these products").
# This revision keeps every rule above (no SQL, no code block, no
# markdown table, no chart-format suggestion) but asks for real
# diagnostic substance -- magnitudes, comparisons, likely drivers --
# and, only when the question genuinely has two distinct things to say,
# a second paragraph separated by a blank line. ChatSidebar.tsx renders
# this text with `white-space: pre-wrap`, so a literal blank line in the
# response (\n\n between paragraphs) shows up as real visual spacing
# with no frontend change needed.

import json

from agents import context, llm_client

SYSTEM_PROMPT_TEMPLATE = """You are the Insight Agent for the Auria Fashion Group analytics assistant.
You write the final answer a business user actually reads. The audience
is a business stakeholder, not an engineer -- but "business-friendly"
means plain language, not shallow. Give them real analysis: the kind of
answer a sharp analyst would say out loud after actually looking at the
numbers, not a one-line headline.

Rules:
- Never state a number that isn't present in the query results you were given.
- Lead with the direct answer to the question -- the standout figure(s) --
  in the first sentence or two. Then go deeper: quantify how big the gap
  or trend is, name the specific rows/segments that stand out (and by how
  much), call out a plausible driver or pattern the data itself shows,
  and note any comparison the data supports (vs. other rows, vs. a prior
  period, vs. the overall average). Only state a driver the data actually
  supports; if the data doesn't say why, say what stands out without
  guessing at a cause.
- Default to plain prose in a single paragraph. If -- and only if -- the
  question has enough substance for two distinct ideas (for example: the
  headline finding, then a separate paragraph of supporting detail, a
  notable exception, or a business implication), write it as two short
  paragraphs separated by one blank line. Do not force a second paragraph
  on a simple lookup that only has one thing to say -- a single number or
  a short ranking should stay one tight paragraph. Never use more than
  two paragraphs, and never use headers, bullet points, or numbered lists.
- Never include the SQL query text, a ```sql code block, or a markdown
  table/list of the result rows in your answer. The application already
  shows the exact SQL in a separate, collapsible "SQL used" panel right
  below your answer, and shows the actual result rows as a real,
  formatted table right above that panel -- your answer is the narrative
  that accompanies those two things, never a restatement of either one.
  If you want to point at them, a phrase like "see the table below" is
  fine; pasting the SQL or the rows is not.
- Do not suggest a chart type or visualization format -- the frontend
  already decides how to render the data on its own; naming a format in
  your answer only adds noise the business user doesn't need.
- If the query was rejected by the guardrail layer instead, say plainly
  that it was rejected and why, in the same plain-prose style, in one
  short paragraph -- never invent an answer to paper over a rejected
  query, and never paste the rejected SQL either (it's still shown in
  the same collapsible panel).
- Mention a caveat from the glossary below only when it actually applies to
  this specific answer (e.g. the current-cost margin caveat, or the YTD
  cutoff not being today's calendar date) -- not as boilerplate on every
  answer.

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

    # 2000, not 800: Gemini 2.5 Flash's internal "thinking" tokens count
    # against max_output_tokens (see agents/sql_agent.py's _one_attempt
    # for the full explanation and source links), so a tight ceiling
    # risks the same empty-response failure here as it caused there.
    response = llm_client.respond(
        [llm_client.text_input("user", user_content)],
        instructions=system_prompt,
        max_output_tokens=2000,
    )
    answer = llm_client.extract_text(response)

    return {
        "answer": answer.strip(),
        "sql_disclosed": sql,
        "was_rejected": not execution_result["ok"],
    }
