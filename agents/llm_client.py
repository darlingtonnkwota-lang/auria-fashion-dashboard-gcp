# LLM client for the agent pipeline -- the GCP replacement for the
# Databricks build's agents/claude_client.py. Same stable interface
# (respond/text_input/extract_text/extract_function_call) so
# sql_agent.py/insight_agent.py/orchestrator.py don't need to change at
# all beyond the import line -- only what's behind the interface changes.
#
# Calls Gemini via Vertex AI (google-genai SDK, vertexai=True mode),
# billed against the same GCP billing account as everything else in this
# project -- the decision locked in in gcp_strategy.md section 5 (full
# switch to Gemini, not a separate Anthropic API key/billing
# relationship). Default model is Gemini 2.5 Flash, matching the
# Haiku-as-default-model cost philosophy from the Databricks build.
#
# Auth: no API key is set or read here. The Vertex AI client uses
# Application Default Credentials automatically -- in Cloud Shell, that's
# already your own gcloud identity, same as agents/guardrails.py's
# BigQuery client needs no separate auth either. If a call 403s, the
# first thing to check is whether your identity has the Vertex AI User
# role (roles/aiplatform.user) on the project -- see
# docs/gcp_phase5_governance_agents_setup.md.

import json
import os

from google import genai
from google.genai import types

PROJECT = os.environ.get("AURIA_GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("AURIA_GCP_LOCATION", "us-central1")
MODEL_NAME = os.environ.get("AURIA_GEMINI_MODEL", "gemini-2.5-flash")

_TOOL_CHOICE_TO_MODE = {"auto": "AUTO", "required": "ANY", "none": "NONE"}


def _client() -> genai.Client:
    if not PROJECT:
        raise RuntimeError(
            "AURIA_GCP_PROJECT (or GOOGLE_CLOUD_PROJECT) is not set. Set it to "
            "your GCP project id, e.g. clientgcpkraftheinzadpoc, before calling "
            "this module."
        )
    return genai.Client(vertexai=True, project=PROJECT, location=LOCATION)


def text_input(role: str, text: str) -> dict:
    """Builds one turn of conversation. role is 'user' or 'assistant'
    (system/developer instructions go through respond()'s `instructions`
    argument instead) -- Gemini's own role name for the model's turn is
    'model', not 'assistant', so that mapping happens here and nowhere
    else needs to know about it."""
    gemini_role = "model" if role == "assistant" else "user"
    return {"role": gemini_role, "parts": [{"text": text}]}


def _to_gemini_tool(flat_tool: dict) -> types.Tool:
    """Converts our flat tool schema (type/name/description/parameters all
    top-level, the same shape the Databricks build's claude_client.py
    used for the Responses API) into a Gemini FunctionDeclaration."""
    declaration = types.FunctionDeclaration(
        name=flat_tool["name"],
        description=flat_tool.get("description", ""),
        parameters=flat_tool["parameters"],
    )
    return types.Tool(function_declarations=[declaration])


def respond(input_items, instructions=None, tools=None, tool_choice="auto", max_output_tokens=2000):
    """One call to Gemini. Returns the raw GenerateContentResponse -- read
    it with extract_text()/extract_function_call(), not directly."""
    client = _client()

    config_kwargs = dict(
        temperature=0.0,
        max_output_tokens=max_output_tokens,
    )
    if instructions:
        config_kwargs["system_instruction"] = instructions
    if tools:
        config_kwargs["tools"] = [_to_gemini_tool(t) for t in tools]
        mode = _TOOL_CHOICE_TO_MODE.get(tool_choice, "AUTO")
        config_kwargs["tool_config"] = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode=mode)
        )

    return client.models.generate_content(
        model=MODEL_NAME,
        contents=list(input_items),
        config=types.GenerateContentConfig(**config_kwargs),
    )


def extract_text(response) -> str:
    """The plain-text portion of a response, if any. response.text raises
    if the response has no text part at all (e.g. it's purely a function
    call) -- guarded here so callers don't need their own try/except."""
    try:
        return response.text or ""
    except (ValueError, AttributeError):
        return ""


def extract_function_call(response, name: str | None = None):
    """Returns (call_name, arguments_dict) for the first function call in
    the response (optionally filtered to a specific tool name), or None if
    the model didn't call one."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    for part in parts:
        call = getattr(part, "function_call", None)
        if call and (name is None or call.name == name):
            args = dict(call.args) if call.args else {}
            return call.name, args
    return None
