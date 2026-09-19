# GCP Phase 0 — Repo, Branching & CI/CD Setup

Goal: a real dev -> prod DevOps loop for the GCP rebuild, kept **fully
separate** from the Azure DevOps repo/billing on purpose — this project
never touches those credits or that repo.

## Why GitHub, not "a repo inside GCP"

Worth naming honestly: Google's own in-console git hosting
(**Cloud Source Repositories**) has been closed to new customers since
June 17, 2024, and its replacement, **Secure Source Manager**, is a
managed enterprise product starting at **$1,000/month per instance** — not
viable for a personal POC. So the realistic, free, and (today) far more
common real-world pattern is what most GCP shops actually do: host the
repo on **GitHub**, and connect it to GCP via a native **Cloud Build
trigger**. That's still fully "connected to GCP" in the sense that matters
— GCP builds and deploys straight off pushes to this repo — it's just not
physically hosted inside a GCP project.

## Branch strategy

- **`main`** = production. Every push triggers a deploy to the `prod`
  Cloud Run service.
- **`dev`** = active development. Every push triggers a deploy to the
  `dev` Cloud Run service.
- **Promotion to prod = a PR from `dev` into `main`, merged in GitHub.**
  No separate manual deploy step — the merge itself *is* the promotion,
  because both branches point at the same `cloudbuild.yaml`, parameterized
  by a `_ENV` substitution that only differs per-trigger.

## One-time setup checklist

### A. GitHub (your machine)

1. github.com/new -> name it `auria-fashion-dashboard-gcp`, **Public**, do
   **not** initialize with a README/.gitignore/license (this repo already
   has its own, committed locally).
2. From a real terminal (not a sandboxed shell) in
   `~/Desktop/kh_github_work/auria-fashion-dashboard-gcp`:
   ```
   git remote add origin https://github.com/<your-username>/auria-fashion-dashboard-gcp.git
   git push -u origin main
   git push -u origin dev
   ```

### B. GCP one-time setup — use **Cloud Shell** (console.cloud.google.com,
top-right `>_` icon) so `gcloud` is already authenticated as you, no local
install needed:

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  aiplatform.googleapis.com

gcloud artifacts repositories create auria \
  --repository-format=docker --location=us-central1

PROJECT_NUMBER=$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### C. Connect Cloud Build to GitHub (console, one-time OAuth)

1. Console -> **Cloud Build -> Triggers -> Connect Repository -> GitHub**,
   authorize the Cloud Build GitHub App, select
   `auria-fashion-dashboard-gcp`.
2. Create trigger **`deploy-dev`**: event = push to branch, branch regex
   `^dev$`, build config = `cloudbuild.yaml`, substitution `_ENV=dev`.
3. Create trigger **`deploy-prod`**: event = push to branch, branch regex
   `^main$`, build config = `cloudbuild.yaml`, substitution `_ENV=prod`.

### D. First validation run (the walking skeleton)

1. Push to `dev` -> confirm `deploy-dev` fires in Cloud Build history ->
   hit the `auria-backend-dev` Cloud Run URL's `/api/health`.
2. Open a PR `dev` -> `main`, merge it -> confirm `deploy-prod` fires ->
   hit `auria-backend-prod`'s `/api/health`.

Once both come back `{"ok": true, ...}`, the pipeline is proven end to end
and every later phase (BigQuery pipelines, agents, forecast, frontend)
lands as normal commits through the same dev -> PR -> main loop — no
pipeline changes needed.

## Why I can't push for you

Worth being upfront about: the sandboxed shell I use to edit files in your
connected folder doesn't carry your GitHub login (no keychain, no cached
credential helper, no `gh` CLI signed in) — by design, it only has
filesystem access, not your account credentials. So every `git push`,
including the very first one, needs to run from your own terminal. I'll
keep committing work to `dev` in your connected folder as each phase
lands; you run the `push`, and the `dev` -> `main` PR merge is the
promotion step you wanted hands-on practice with anyway.

## Known, intentional simplifications for a POC

- `--allow-unauthenticated` on both Cloud Run services for now (easiest to
  demo/click a URL) — tighten to authenticated-only before anything public
  facing, the same instinct as the Databricks dashboard's
  allow-approved-domains note.
- No Terraform/IaC layer — the four `gcloud` commands above are a
  one-time, hand-run setup, not something re-run per deploy. Worth
  revisiting only if this grows past a POC.
- BigQuery/Vertex AI IAM (service accounts for the agents, dataset-level
  grants) isn't part of this CI/CD setup — that's Phase 5 governance work,
  scoped in `gcp_strategy.md`.
