# Auria Fashion Group — GCP Edition

This is the **GCP twin** of the Databricks-based Auria Fashion Group agentic
dashboard (that build lives in a separate Azure DevOps repo). Same fictional
retailer, same governed-agent architecture (Orchestrator → SQL Agent →
Validation/Execution Agent → Insight/Viz Agent), same synthetic dataset —
rebuilt on BigQuery + Vertex AI (Gemini), with a fully native in-app
dashboard (Recharts, not an embedded BI report) instead of Databricks +
Claude + AI/BI Dashboards.

Kept as a **fully separate repo** on purpose: independent of the Azure
DevOps repo/billing, so this build never competes with that project's
resources or credits.

See `docs/gcp_phase0_devops_setup.md` for how this repo, its branches, and
its CI/CD pipeline are wired up. Later phase docs land in `docs/` the same
way the Databricks build's `docs/phaseN_*.md` files did.

## Branch strategy

- **`main`** — production. Every push here is auto-deployed to the `prod`
  Cloud Run services by Cloud Build.
- **`dev`** — active development. Every push here is auto-deployed to the
  `dev` Cloud Run services. This is where day-to-day commits land.
- **Promotion to prod = opening a PR from `dev` into `main` and merging it
  in GitHub.** That merge is the actual "promote to prod" action — no
  separate deploy step, no manual `gcloud run deploy`. That's the whole
  point of the pipeline.

## Repo layout

```
pipelines/    Bronze/Silver/Gold/forecast BigQuery SQL + loaders
context/      git-tracked glossary / metric specs / example questions
              (ported from the Databricks build, table refs repointed)
agents/       orchestrator / SQL / validation / insight agent code
app/          FastAPI backend: Phase 5's agent pipeline over HTTP
              (POST /api/ask) + the native dashboard's data endpoints
              (GET /api/dashboard/*), both querying BigQuery directly
              (Phase 7 -- was a walking-skeleton health check through Phase 6)
frontend/     Next.js app -- a fully native dashboard (Recharts charts
              and tables, not an embedded BI report) plus the "Ask a
              question" chat sidebar, forked from the Databricks build's
              frontend shell and redesigned dark/colorful (Phase 7)
docs/         phase-by-phase setup docs, same convention as the Azure repo
cloudbuild.yaml   one Cloud Build config, parameterized by `_ENV`
                  (dev or prod), building + deploying BOTH the backend
                  and frontend as separate Cloud Run services (Phase 7)
```
