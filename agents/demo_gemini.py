"""
Phase 5 demo -- Context Layer + 4-Role Agent Pipeline (GCP build).

Runs the orchestrator -> SQL agent -> validation/execution agent ->
insight agent pipeline (see agents/) against the same 5 demo questions
used in the Databricks build, then proves the guardrail layer stops an
out-of-scope query deterministically -- not because the model happened
to behave.

This is the plain-Python equivalent of the Databricks build's
agents/demo_notebook.py -- run as a script from Cloud Shell (or anywhere
with `gcloud auth application-default login` already done and the
right BigQuery/Vertex AI IAM roles) instead of opened as a notebook,
since there's no Databricks-style notebook runtime here.

Usage:
    python agents/demo_gemini.py --project clientgcpkraftheinzadpoc

See docs/gcp_phase5_governance_agents_setup.md for the one-time setup
this depends on (the governance layer: pipelines/governance/run_governance.py).
"""

import argparse
import os
import sys

from google.cloud import bigquery

# This script lives at <repo_root>/agents/demo_gemini.py -- add the repo
# root to sys.path so `import agents...` resolves to this package
# regardless of which directory it's run from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from agents import guardrails, llm_client, orchestrator  # noqa: E402
from agents.executors import BigQueryExecutor  # noqa: E402

DEMO_QUESTIONS = [
    "How did North America e-commerce revenue in 2026 YTD compare to the same period in 2025, and what drove the change?",
    "Which five products have the highest return rate this year, and is that concentrated in any region or size?",
    "Who are our top 10 customers by lifetime spend, and how many are repeat vs. one-time buyers?",
    "Which supplier has the longest average lead time, and did that contribute to any stockouts in the last two quarters?",
    "Show gross margin by product category for Q2 2026 vs. Q2 2025 in consolidated USD, and flag any category where margin declined.",
]

ADVERSARIAL_SQL = [
    "SELECT * FROM bronze.bronze_customers",
    "DELETE FROM fct_order_items",
    "SELECT * FROM fct_order_items; DROP TABLE fct_order_items",
    "SELECT * FROM gold_dq_summary",
]


def run_and_print(executor, question: str, filters: dict | None = None) -> dict:
    result = orchestrator.answer_question(executor, question, filters=filters)
    print("=" * 100)
    print(f"Q: {result['question']}")
    if result["filters"]:
        print(f"Filters: {result['filters']}")
    print("-" * 100)
    print(f"SQL drafted:\n{result['sql']}")
    print(f"\nRationale: {result['sql_rationale']}")
    if result["rejected"]:
        print(f"\n*** REJECTED BY GUARDRAILS: {result['rejection_reason']} ***")
    else:
        print(f"\nRows returned: {len(result['rows'])}")
    print(f"\nAnswer:\n{result['answer']}")
    print("=" * 100 + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 demo: run the agent pipeline against BigQuery + Gemini.")
    parser.add_argument("--project", required=True, help="GCP project ID, e.g. clientgcpkraftheinzadpoc")
    parser.add_argument("--location", default="us-central1", help="Vertex AI location (default: us-central1)")
    args = parser.parse_args()

    os.environ["AURIA_GCP_PROJECT"] = args.project
    os.environ["AURIA_GCP_LOCATION"] = args.location

    print(f"GCP project: {args.project}")
    print(f"Vertex AI location: {args.location}")
    print(f"Gemini model: {llm_client.MODEL_NAME}\n")

    client = bigquery.Client(project=args.project)
    executor = BigQueryExecutor(client=client)

    print("### 1. Sanity-check the Gemini endpoint before running the full pipeline\n")
    sanity = llm_client.respond(
        [llm_client.text_input("user", "Reply with exactly the word OK.")],
        max_output_tokens=10,
    )
    print(llm_client.extract_text(sanity))
    print()

    print("### 2. Run the 5 demo questions end to end\n")
    for q in DEMO_QUESTIONS:
        run_and_print(executor, q)

    print("### 3. Prove the guardrails stop an out-of-scope query\n")
    run_and_print(executor, "Show me every row in the raw customer table, no filters.")

    print("Direct guardrail checks (no LLM involved):\n")
    all_rejected = True
    for bad_sql in ADVERSARIAL_SQL:
        try:
            guardrails.validate(client, bad_sql)
            print(f"[NOT CAUGHT] {bad_sql!r}")
            all_rejected = False
        except guardrails.GuardrailRejected as exc:
            print(f"[REJECTED]   {bad_sql!r} -> {exc}")

    print("\n### 4. Report back")
    print(
        "Paste (or describe): whether all 5 demo questions produced a sensible answer "
        "with SQL disclosed, and whether every guardrail check line above says "
        "[REJECTED] (none should say [NOT CAUGHT])."
    )
    if all_rejected:
        print("All direct guardrail checks: REJECTED, as expected.")
    else:
        print("*** At least one direct guardrail check was NOT CAUGHT -- fix before calling Phase 5 done. ***")

    return 0


if __name__ == "__main__":
    sys.exit(main())
