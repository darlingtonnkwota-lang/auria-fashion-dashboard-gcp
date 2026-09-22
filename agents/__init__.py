# Auria Fashion Group -- agents package (GCP build, Phase 5).
#
# Four logical roles (orchestrator, sql_agent, validation_agent,
# insight_agent) living in one small Python package rather than four
# separate services, per gcp_strategy.md section 5 -- ported from the
# Databricks build's agents/ package with the same role split. Each
# module still has exactly one job -- see its own docstring. The only
# real changes from the Databricks version: llm_client.py calls Gemini
# via Vertex AI instead of Claude via a Databricks model service, and
# guardrails.py/executors.py talk to BigQuery instead of Spark/a SQL
# Warehouse. sql_agent.py, validation_agent.py, insight_agent.py, and
# orchestrator.py are otherwise the same logic, just importing
# llm_client instead of claude_client.
