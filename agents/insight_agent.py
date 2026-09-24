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
# of what this agent says -- so that instruction was pure dead weight,
# and the model's most natural way to "disclose the SQL" was to paste
# it. This agent's only job now is the plain-English narrative that goes
# with those two things, not a restatement of either.
#
# Second round of feedback, after the SQL/table fix landed: the fix
# traded too far toward terse -- a flat single paragraph read as "one
# mushed up paragraph" and too high-level for diagnostic questions. That
# revision asked for real substance and allowed a second paragraph "when
# warranted" -- but in practice the model kept defaulting to one
# paragraph even for genuinely multi-part diagnostic answers (e.g. a
# correlation question backed by four separate product examples), so a
# third round below makes the two-paragraph split the default for any
# answer with real analytical content, not just an optional escape
# hatch, and reserves one paragraph for truly simple lookups only.
#
# Third round (this revision): two changes. (1) The paragraph-break rule
# is now a concrete template (headline paragraph, then supporting-detail
# paragraph) instead of a soft "if warranted" suggestion, because the
# soft version wasn't reliably triggering. (2) The frontend now renders
# its own static "Analysis" heading above every answer
# (ChatSidebar.tsx), so this prompt explicitly tells the model not to
# add its own heading/label line -- avoiding a doubled-up "Analysis /
# Analysis:" look. ChatSidebar.tsx renders the answer with
# `white-space: pre-wrap`, so a literal blank line in the response
# (\n\n between paragraphs) shows up as real visual paragraph spacing
# with no other frontend change needed.

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
- Structure: write two short paragraphs, separated by exactly one blank
  line, for any answer that involves a comparison, a ranking, a trend, a
  driver, or more than one noteworthy data point -- which is nearly
  every one of these business questions. First paragraph: the direct
  answer to the question -- the standout figure(s) -- in 1-3 sentences.
  Second paragraph: back it up with real substance -- name the specific
  rows/segments that stand out and by how much, quantify the size of
  the gap or trend, call out a plausible driver or pattern the data
  itself shows (only if the data actually supports it -- never invent a
  cause), and note a comparison the data supports (vs. other rows, a
  prior period, or the overall average). Only fall back to a single
  short paragraph when the question is a genuinely simple lookup with
  nothing more to add -- one number, one name, a yes/no. Never use more
  than two paragraphs, and never use headers, bullet points, or
  numbered lists inside a paragraph.
- Do not start your answer with a heading, label, or restatement of the
  question (e.g. do not write "Analysis:", "Summary:", or "Answer:") --
  the application already shows its own heading above your answer, so
  starting with one of your own would just duplicate it. Start directly
  with the finding.
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
