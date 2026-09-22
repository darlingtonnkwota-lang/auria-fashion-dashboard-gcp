# The Validation/Execution agent's guardrail layer -- the "governed,
# auditable, read-only" boundary from gcp_strategy.md section 4. Before
# any SQL Agent-drafted query touches real data, it is:
#
#   1. checked against a real BigQuery SQL function
#      (pipelines/governance/sql/01_validate_gold_sql.sql), so the check
#      itself is an auditable object with its own job history entry --
#      not just an in-process Python `if` that anyone importing this
#      module directly could bypass -- then
#   2. capped at a hard row limit and a wall-clock timeout before it's
#      allowed to execute at all.
#
# Direct port of the Databricks build's agents/guardrails.py: same
# constants, same two functions, same GuardrailRejected exception --
# only the underlying calls change (a BigQuery Client instead of a
# SparkSession).
#
# Known limitation for this POC, documented on purpose rather than
# missed (same limitation the Databricks build named): validate_gold_sql
# uses regex checks, not a real SQL parser, and this code runs under the
# calling user's own gcloud identity rather than a dedicated read-only
# service account scoped to SELECT-only grants on the `authorized`
# dataset. A production build would do both properly -- a real SQL
# parser (e.g. sqlglot) for the table/keyword checks, and a service
# account whose IAM grants do the actual enforcement, so a compromised or
# buggy agent literally cannot act outside its allow-list no matter what
# Python code runs. For a demo dataset with no sensitive data and no
# write path anywhere in Gold, the regex + row-limit + timeout
# combination below is enough to prove the pattern end to end.

import concurrent.futures
import re

from google.cloud import bigquery

DATASET = "gold"
AUTHORIZED_DATASET = "authorized"
MAX_ROWS = 500
TIMEOUT_SECONDS = 30

# Kept here as the human-readable mirror of
# pipelines/governance/sql/02_authorized_views.sql and
# context/schema_reference.yaml's object list -- not read by
# validate_gold_sql itself (that function only checks dataset/keyword
# patterns, not this exact set), but used by callers/tests that want to
# sanity-check a query's tables before even calling the BigQuery
# function. 19 objects -- gold_sales_forecast (Phase 6) is the newest
# addition.
ALLOWED_TABLES = {
    "dim_customer",
    "dim_product",
    "dim_supplier",
    "dim_store",
    "dim_warehouse",
    "dim_promotion",
    "dim_date",
    "fct_order_items",
    "fct_returns",
    "fct_purchase_order_lines",
    "fct_inventory_snapshots",
    "gold_monthly_kpis",
    "gold_ytd_by_year",
    "gold_top_products_monthly",
    "gold_top_customers_monthly",
    "gold_returns_by_product_monthly",
    "gold_channel_performance",
    "gold_supplier_performance",
    "gold_sales_forecast",
}

# Governance demo addition -- requested to make an explicit point when
# showing this to stakeholders: a question naming a personal-identifier
# category this dataset NEVER collected anywhere (no SIN/SSN, phone,
# mailing address, date of birth, or government-ID column exists in
# Bronze/Silver/Gold at all) must be REJECTED outright, not answered with
# "I couldn't find that" -- that phrasing implies a search happened and
# came up empty, which would wrongly suggest the assistant *would*
# disclose the value if a matching row existed. Checked here, in plain
# Python, before the SQL agent or BigQuery are even called, so the
# rejection is instant and deterministic -- it never depends on the LLM
# correctly recognizing the request as out of scope.
#
# This is deliberately separate from the dim_customer.email case (which
# IS a real column -- see pipelines/governance/sql/01_validate_gold_sql.sql
# for that enforcement). Nothing below has ever existed as a column, so
# there is no query that could ever answer it, regardless of phrasing.
RESTRICTED_TOPIC_PATTERNS = [
    (r"\bsin\b|social insurance", "a social insurance number (SIN)"),
    (r"\bssn\b|social security", "a social security number (SSN)"),
    (r"passport", "a passport number"),
    (r"driver'?s?\s+licen[sc]e", "a driver's license number"),
    (r"credit card|debit card|card number|cvv", "a payment card number"),
    (r"bank account|routing number|iban\b", "a bank account number"),
    (r"date of birth|\bdob\b|birth ?date", "a date of birth"),
    (r"phone number|telephone number|cell(?:phone)? number|mobile number", "a phone number"),
    (r"home address|mailing address|street address|residential address", "a home address"),
    (r"tax id|government id|national id|driver'?s?\s+id", "a government ID number"),
]


def check_restricted_topic(question: str) -> str | None:
    """Returns a rejection message if the question asks for a personal-
    identifier category that has never existed anywhere in this dataset,
    else None. Called by orchestrator.answer_question before the SQL
    agent drafts anything.

    Keyword-based on purpose, not a schema lookup: these fields were
    never collected in Bronze/Silver/Gold in the first place (unlike
    email, which does exist and is blocked separately, at the SQL layer,
    because it's a real column an agent could still reference). No
    amount of clever SQL could ever answer one of these -- the rejection
    is about the request, not about what a query returned.
    """
    lowered = question.lower()
    for pattern, label in RESTRICTED_TOPIC_PATTERNS:
        if re.search(pattern, lowered):
            return (
                f"This asks for {label}, which this dataset has never collected and this "
                "assistant will never expose. That's a data governance rule, not a search "
                "that came up empty -- personal identifiers like this aren't in scope "
                "regardless of whether a matching customer exists. The customer data "
                "available here is limited to business attributes: name, region, "
                "lifetime spend, and order history."
            )
    return None


class GuardrailRejected(Exception):
    """Raised when the BigQuery validation function rejects a query, or a
    query exceeds the row/timeout guardrails."""


def validate(client: bigquery.Client, sql_text: str) -> None:
    """Calls <project>.gold.validate_gold_sql. Raises GuardrailRejected if
    it returns anything other than 'OK'.

    Passes sql_text as a query parameter rather than splicing it into the
    query string by hand. A hand-escaped string literal (replacing only
    `'` with `\\'`) breaks the moment the drafted SQL is multi-line --
    BigQuery's quoted string literals don't allow a raw embedded newline,
    so that approach throws "Unclosed string literal" on any real,
    multi-line agent-drafted query. A query parameter sidesteps escaping
    entirely, for quotes, newlines, and backslashes alike."""
    verdict_sql = f"SELECT `{client.project}.{DATASET}.validate_gold_sql`(@sql_text) AS verdict"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("sql_text", "STRING", sql_text)]
    )
    rows = list(client.query(verdict_sql, job_config=job_config).result())
    verdict = rows[0]["verdict"]
    if verdict != "OK":
        raise GuardrailRejected(verdict)


def execute(client: bigquery.Client, sql_text: str):
    """Validate, then run sql_text with a row cap and a wall-clock timeout,
    with the default dataset pinned to `authorized` (BigQuery's version
    of the Databricks build's catalog/schema pinning) so the SQL agent's
    unqualified table names resolve correctly. Returns
    (rows_as_list_of_dicts, columns). Raises GuardrailRejected on any
    failure -- validation_agent.py turns that into a message the insight
    agent can explain to the user, rather than letting an exception
    bubble up as a crash."""
    validate(client, sql_text)

    capped_sql = f"SELECT * FROM ({sql_text.rstrip(';')}) AS agent_query LIMIT {MAX_ROWS}"
    job_config = bigquery.QueryJobConfig(
        default_dataset=f"{client.project}.{AUTHORIZED_DATASET}"
    )

    def _run():
        query_job = client.query(capped_sql, job_config=job_config)
        result_iter = query_job.result(timeout=TIMEOUT_SECONDS)
        columns = [field.name for field in result_iter.schema]
        rows = [dict(row.items()) for row in result_iter]
        return rows, columns

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        try:
            return future.result(timeout=TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise GuardrailRejected(
                f"Query exceeded the {TIMEOUT_SECONDS}s guardrail timeout and was cancelled."
            )
        except Exception as exc:  # noqa: BLE001 -- surfaced to the caller either way
            raise GuardrailRejected(f"Query failed: {exc}") from exc
