# Phase 7 -- built from the REPO ROOT as build context (see cloudbuild.yaml's
# build-backend step: `docker build -f app/Dockerfile .`), not from ./app
# alone. This lets the backend import the repo root's agents/ and context/
# packages directly, copied in below -- no vendored duplicate + sync
# script needed (that trick, in the Databricks build's backend/, existed
# only to work around Vercel's per-project file tracing; Cloud Build has
# no such restriction, so a real repo-root context is simpler and the
# repo root's agents/ and context/ always stay the single source of truth).
FROM python:3.12-slim

WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/*.py ./
COPY agents/ ./agents/
COPY context/ ./context/

# Cloud Run injects $PORT; default to 8080 for local runs.
ENV PORT=8080
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
