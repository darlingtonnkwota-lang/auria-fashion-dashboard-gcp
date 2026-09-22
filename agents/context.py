# Loads the version-controlled business context layer (context/*.yaml) and
# formats it into the text each agent role gets in its system prompt.
#
# This is the "grounding" that keeps the SQL agent from guessing column
# names or reinventing metric formulas from scratch. To teach the agents
# something new, edit the YAML files under context/ -- not this loader.
#
# Ported unchanged from the Databricks build's agents/context.py -- this
# module has no platform-specific code at all, it just reads YAML and
# formats text.

import os

import yaml

_CONTEXT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "context"
)


def _load(name):
    path = os.path.join(_CONTEXT_DIR, name)
    with open(path) as f:
        return yaml.safe_load(f)


def load_all():
    return {
        "glossary": _load("business_glossary.yaml"),
        "metrics": _load("metric_specs.yaml"),
        "schema": _load("schema_reference.yaml"),
        "examples": _load("example_questions.yaml"),
    }


def build_sql_agent_context() -> str:
    """Everything the SQL agent needs: schema + metric formulas + glossary
    rules + worked examples. Formatted as readable text rather than a raw
    YAML dump, to keep token usage (and cost) reasonable."""
    ctx = load_all()
    parts = ["## Business glossary\n"]
    for term, spec in ctx["glossary"]["terms"].items():
        parts.append(f"- **{term}**: {spec['definition'].strip()}")
        if spec.get("caveat"):
            parts.append(f"  (caveat: {spec['caveat'].strip()})")

    parts.append("\n## Hard rules\n")
    for rule in ctx["glossary"]["rules"]:
        parts.append(f"- {rule}")

    parts.append("\n## Metric formulas (reuse these exact expressions)\n")
    for name, spec in ctx["metrics"]["metrics"].items():
        parts.append(
            f"- **{name}** (source: {spec['source']}, grain: {spec['grain']}): "
            f"`{spec['canonical_sql'].strip()}`"
        )
        if spec.get("notes"):
            parts.append(f"  note: {spec['notes'].strip()}")

    parts.append(
        "\n## Schema (the gold dataset, via the `authorized` views) -- only "
        "these objects may be queried, and write table names UNQUALIFIED "
        "(e.g. `dim_product`, not `project.gold.dim_product`)\n"
    )
    schema = ctx["schema"]
    for section in ("dimensions", "facts", "curated_views"):
        parts.append(f"\n### {section}\n")
        for obj_name, spec in schema[section].items():
            parts.append(
                f"- **{obj_name}** (grain: {spec['grain']}): columns = {spec['columns']}"
            )
            for j in spec.get("joins", []):
                parts.append(f"  join: {j}")
            if spec.get("notes"):
                parts.append(f"  note: {spec['notes'].strip()}")

    parts.append("\n## Worked examples\n")
    for ex in ctx["examples"]["demo_questions"]:
        parts.append(
            f"- Q: {ex['question'].strip()}\n"
            f"  approach: {ex['approach'].strip()}\n"
            f"  tables: {ex['tables']}"
        )

    return "\n".join(parts)


def build_insight_agent_context() -> str:
    """A lighter version for the insight agent -- just the glossary, so it
    explains numbers using the same definitions the SQL agent used. It
    never writes SQL itself, so it doesn't need the full schema."""
    ctx = load_all()
    parts = ["## Business glossary\n"]
    for term, spec in ctx["glossary"]["terms"].items():
        parts.append(f"- **{term}**: {spec['definition'].strip()}")
        if spec.get("caveat"):
            parts.append(f"  (caveat: {spec['caveat'].strip()})")
    return "\n".join(parts)
