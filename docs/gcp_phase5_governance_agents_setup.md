# GCP Phase 5 — Governance Layer + 4-Role Agent Pipeline Setup Guide

Goal: a version-controlled business context layer (`context/`), a
governed BigQuery validation function + authorized views
(`pipelines/governance/`), and a hand-rolled 4-role agent pipeline
(`agents/`) that answers the same 5 demo questions as the Databricks
build — with SQL disclosed on every answer, and an out-of-scope query
stopped by a real guardrail, not by luck.

**Status: ready to run.** All governance SQL, context YAML, and agent
Python modules are committed to `dev`.

## 0. The LLM decision

**Decided: Gemini via Vertex AI**, not Claude — see `gcp_strategy.md`'s
Open Decisions section for the full reasoning (keeping Claude would have
meant a third, separate billing relationship on top of the GCP account
already running this project). `agents/llm_client.py` calls Gemini
2.5 Flash via the `google-genai` SDK in `vertexai=True` mode, billed
through the same GCP billing account as BigQuery. No API key is set
anywhere — it uses Application Default Credentials, the same auth
Cloud Shell already gives every other script in this repo.

If a call 403s, check that your identity has the **Vertex AI User**
role (`roles/aiplatform.user`) on the project — everything else
(`aiplatform.googleapis.com`) was already enabled back in Phase 0.

## 1. What's different from the Databricks build, and what isn't

The business logic — the glossary, metric formulas, schema semantics,
worked examples, the four-role split (orchestrator → SQL agent →
validation/execution agent → insight agent), and the "SQL disclosed,
never fabricate a number" contract — all carry over **identically**.
What changes is the platform underneath:

| Databricks | GCP (this phase) |
|---|---|
| Unity Catalog SQL function (`validate_gold_sql`) | BigQuery persistent SQL function, same name, same regex rules, same rejection reasons |
| Unity Catalog grants + authorized views (governance) | BigQuery IAM + an `authorized` dataset of views over `gold` (see §2's honesty note) |
| `agents/claude_client.py` — Claude via a Databricks model service | `agents/llm_client.py` — Gemini via Vertex AI (`google-genai` SDK) |
| Two executors (`SparkExecutor` for a live notebook, `WarehouseExecutor` for the stateless backend) | **One** executor, `BigQueryExecutor` — BigQuery's client library works identically in a script or a backend, so there's no live-cluster-vs-warehouse split to abstract over. A GCP simplification, not a gap. |
| Tested via a Databricks notebook (`agents/demo_notebook.py`) | Tested via a plain Python script (`agents/demo_gemini.py`), run from Cloud Shell |
| `sql_agent.py`, `validation_agent.py`, `insight_agent.py`, `orchestrator.py` | **Unchanged logic** — only `sql_agent.py`/`insight_agent.py` needed a one-line import swap (`llm_client` instead of `claude_client`); `validation_agent.py`/`orchestrator.py` are executor-agnostic and didn't change at all |

## 2. Decisions this phase locks in

- **SQL agent scope = the whole `gold` dataset** (via `authorized`
  views), not just the 7 curated `gold_*` views — same reasoning as
  Databricks: the demo questions need direct fact/dimension joins
  (lifetime customer value, return concentration by region, stockouts
  tied to a specific supplier) that the curated views alone don't cover.
  `gold_dq_summary` is explicitly excluded — internal reconciliation
  table, not a reporting object.
- **18 allowed objects, not 19.** The Databricks build's allow-list has
  19 because it already had `gold_sales_forecast` built (its Phase 7).
  This GCP build's forecast phase (Phase 6) hasn't happened yet, so
  `gold_sales_forecast` doesn't exist — referencing it now would just
  fail at execution with "table not found," not a meaningful guardrail
  test. It'll be added to `context/schema_reference.yaml`,
  `context/metric_specs.yaml`, `context/example_questions.yaml`, and
  `agents/guardrails.py`'s `ALLOWED_TABLES` once Phase 6 actually builds
  that table — matching the Databricks build's question set exactly at
  that point.
- **Hand-rolled tool-calling loop, not a framework** — `agents/llm_client.py`
  calls Gemini directly, no LangChain/AgentExecutor, every prompt/tool
  call/guardrail check is plain Python you can read top to bottom.
- **Governed execution = a real BigQuery SQL function**, not just a
  Python `if` statement — see the honesty note below for what this does
  and doesn't enforce yet.
- **One model for all four roles** (Gemini 2.5 Flash) — the cost
  difference of a tiered setup is immaterial at demo volume, and one
  model keeps this phase simpler to reason about and debug, same call
  the Databricks build made with Llama/Claude.
- **Tested via a plain Python script**, not a notebook — there's no
  Databricks-notebook-equivalent runtime on GCP, so `agents/demo_gemini.py`
  is a normal script you run with `python`, not something you "open" in
  a special way. The agent logic itself lives in plain importable
  modules under `agents/`, exactly like Databricks — Phase 7's backend
  will reuse `agents.orchestrator.answer_question(...)` as-is; this
  script is just today's test harness for it.

**Honesty note on the governance layer, matching the Databricks build's
own documented limitation:** `pipelines/governance/sql/02_authorized_views.sql`
creates the views, but making BigQuery's "authorized view" feature the
actual *enforced* boundary needs one more step this repo doesn't
automate: sharing `authorized`'s views as authorized views on `gold`
(`bq update --view_authorization` or Console → `gold` dataset → Sharing
→ Authorized views), then granting a dedicated service account
`roles/bigquery.dataViewer` on `authorized` **only**, never on `gold`
directly. This POC runs everything under your own gcloud identity, which
already has direct access to `gold` — so right now the views are the
*pattern*, not yet the *enforcement*, exactly like the Databricks build
running under your own workspace identity instead of a scoped service
principal. Worth doing properly before this goes in front of Kraft Heinz
stakeholders beyond the immediate team; not blocking for the POC.

## 3. Run it — Cloud Shell

```bash
cd ~/auria-fashion-dashboard-gcp
git pull origin dev
source .venv/bin/activate
pip install -r requirements.txt   # picks up google-genai, pyyaml
```

**Step 1 — governance layer** (creates the `authorized` dataset + its 18
views, and the `validate_gold_sql` function in `gold`):

```bash
python pipelines/governance/run_governance.py --project clientgcpkraftheinzadpoc
```

Sanity-check the function directly:

```bash
bq query --use_legacy_sql=false \
  "SELECT \`clientgcpkraftheinzadpoc.gold.validate_gold_sql\`('SELECT 1')"                                    # OK
bq query --use_legacy_sql=false \
  "SELECT \`clientgcpkraftheinzadpoc.gold.validate_gold_sql\`('DELETE FROM fct_order_items')"                 # REJECTED
bq query --use_legacy_sql=false \
  "SELECT \`clientgcpkraftheinzadpoc.gold.validate_gold_sql\`('SELECT * FROM gold_dq_summary')"               # REJECTED
```

**Step 2 — the demo pipeline:**

```bash
python agents/demo_gemini.py --project clientgcpkraftheinzadpoc
```

This will:
- sanity-check the Gemini endpoint with one small call,
- run all 5 demo questions end to end and print the drafted SQL,
  rationale, row count, and final answer for each,
- run one adversarial question through the full pipeline, then call
  `agents.guardrails.validate()` directly with four hand-written
  malicious SQL strings — bypassing the LLM entirely — to prove the
  stop is deterministic.

## 4. Validate

For each of the 5 demo questions, check that the printed output shows:
sensible SQL against the gold objects only, a rationale that names any
assumption made, and an answer that only cites numbers actually present
in the row output (spot-check one or two against a manual query if a
number looks off).

For the guardrail section, every line under "Direct guardrail checks"
must say `[REJECTED]` — if even one says `[NOT CAUGHT]`, the validation
function needs fixing before this phase can be called done.

## 5. Report back

Paste (or describe) the demo script's output: whether all 5 questions
were answered sensibly with SQL disclosed, and whether every guardrail
check line reads `[REJECTED]`. If both hold, Phase 5 is done and we move
to Phase 6 (BigQuery ML forecasting — `ARIMA_PLUS`, plus `AI.FORECAST` as
a documented alternative).

## Cost note

Each demo-script run makes roughly 15–20 Gemini calls (SQL + insight
agent, one round-trip each, across 6 questions plus the sanity check) at
a few thousand tokens apiece — well under a dollar per run at Gemini
2.5 Flash pricing. The guardrail-only checks in section 3 make no LLM
calls at all.
