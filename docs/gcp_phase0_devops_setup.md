# GCP Phase 0 — Repo, Branching & CI/CD Setup

Goal: a real dev -> prod DevOps loop for the GCP rebuild, kept **fully
separate** from the Azure DevOps repo/billing on purpose — this project
never touches those credits or that repo.

**Status: done.** Both `deploy-dev` and `deploy-prod` builds have run
green against the walking-skeleton backend as of 2026-09-19. Everything
below is the reference for how it's wired, and what to redo if this ever
needs setting up on another machine/project.

## Why GitHub, not "a repo inside GCP"

Worth naming honestly: Google's own in-console git hosting
(**Cloud Source Repositories**) has been closed to new customers since
June 17, 2024, and its replacement, **Secure Source Manager**, is a
managed enterprise product starting at **$1,000/month per instance** — not
viable for a POC. So the realistic, free, and (today) far more common
real-world pattern is what most GCP shops actually do: host the repo on
**GitHub**, and connect it to GCP via a native **Cloud Build trigger**.
That's still fully "connected to GCP" in the sense that matters — GCP
builds and deploys straight off pushes to this repo — it's just not
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

## Repo

New, separate repo: **`auria-fashion-dashboard-gcp`**, public on GitHub
under the account **`darlingtonnkwota-lang`**, cloned locally at
`~/Desktop/kh_github_work/auria-fashion-dashboard-gcp` (sibling to the
Azure DevOps repo's local clone, but otherwise unrelated). GCP project:
`clientgcpkraftheinzadpoc` (the Kraft Heinz demo POC project, under the
`applydigital.co` org).

Scaffolded so far: `.gitignore`, `README.md`, `cloudbuild.yaml` (one
config, `_ENV`-parameterized), a walking-skeleton FastAPI service in
`app/` (`/api/health` only, for now), and placeholder folders for
`pipelines/`, `context/`, `agents/`, `frontend/` that later phases fill
in.

## One-time setup checklist

### A. GitHub + local git identity

1. github.com/new -> name it `auria-fashion-dashboard-gcp`, **Public**, do
   **not** initialize with a README/.gitignore/license.
2. **Use SSH, not HTTPS, for the remote** — this is the one real gotcha
   worth flagging. If your Mac's git/keychain already has HTTPS
   credentials cached for a *different* GitHub account (e.g. a work
   account), git will silently reuse those and every push gets rejected
   with a confusing "permission denied" or "invalid token," even with a
   fresh personal access token in the URL. SSH sidesteps this entirely:
   ```
   ssh-keygen -t ed25519 -C "darlingtonnkwota-lang@github"
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   pbcopy < ~/.ssh/id_ed25519.pub
   ```
   Then on github.com (logged in as `darlingtonnkwota-lang`): **Settings
   -> SSH and GPG keys -> New SSH key**, paste, save.
3. Point the repo at SSH and push:
   ```
   git remote set-url origin git@github.com:darlingtonnkwota-lang/auria-fashion-dashboard-gcp.git
   git push -u origin main
   git push -u origin dev
   ```
   Test the SSH connection first with `ssh -T git@github.com` if you want
   to confirm it's authenticated before pushing — it should greet you by
   username.

### B. GCP one-time setup — use **Cloud Shell** (console.cloud.google.com,
top-right `>_` icon) so `gcloud` is already authenticated, no local
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
```

**The permissions gotcha, found the hard way:** Cloud Build triggers in
current GCP run as the **default Compute Engine service account**
(`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`), *not* the
classic `<PROJECT_NUMBER>@cloudbuild.gserviceaccount.com` account most
older docs/tutorials reference. Grant the roles to the **compute**
account:

```bash
PROJECT_NUMBER=$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${COMPUTE_SA}" --role="roles/iam.serviceAccountUser"
```

Without all four, the build fails in sequence — first at the `build` step
(can't write logs), then `push` (can't upload to Artifact Registry), then
`deploy` (can't act as Cloud Run admin / can't act-as the runtime service
account) — each one surfacing only after the previous is fixed, since
Cloud Build only reports the next failure once the current step's
permission is granted. Granting all four up front avoids three separate
failed-build round trips.

### C. Connect Cloud Build to GitHub (console, one-time OAuth)

1. Console -> **Cloud Build -> Triggers -> Connect Repository -> GitHub**,
   authorize the Cloud Build GitHub App, select
   `auria-fashion-dashboard-gcp`.
2. Create trigger **`deploy-dev`**: event = push to branch, branch regex
   `^dev$`, build config = `cloudbuild.yaml`, substitution `_ENV=dev`.
3. Create trigger **`deploy-prod`**: event = push to branch, branch regex
   `^main$`, build config = `cloudbuild.yaml`, substitution `_ENV=prod`.

### D. First validation run (the walking skeleton) — done

1. Manually ran `deploy-dev` via the trigger's **Run** button (no new
   commit needed since the trigger was created after the initial push) ->
   succeeded on the second retry, after the IAM fixes in §B -> confirmed
   `auria-backend-dev`'s `/api/health` responds.
2. `deploy-prod` fires the same way once a `dev` -> `main` PR is merged —
   same compute service account, same project-level IAM grants, so no
   repeat permission fixes expected.

Every later phase (BigQuery pipelines, agents, forecast, frontend) lands
as normal commits through the same dev -> PR -> main loop — no pipeline
changes needed.

## Why Claude can't push directly

The sandboxed shell used to edit files in the connected folder doesn't
carry Darlington's GitHub login (no keychain, no cached credential
helper, no `gh` CLI signed in, and no SSH key of Darlington's) — by
design, it only has filesystem access, not account credentials. So every
`git push` runs from Darlington's own terminal. Claude keeps committing
work to `dev` in the connected folder as each phase lands; Darlington
runs the `push`, and the `dev` -> `main` PR merge is the promotion step he
wanted hands-on DevOps practice with.

## Known, intentional simplifications for a POC

- `--allow-unauthenticated` on both Cloud Run services for now (easiest to
  demo/click a URL) — tighten to authenticated-only before anything public
  facing, the same instinct as the Databricks dashboard's
  allow-approved-domains note. Worth doing before this is shown to Kraft
  Heinz stakeholders beyond the immediate team.
- No Terraform/IaC layer — the `gcloud` commands above are a one-time,
  hand-run setup, not something re-run per deploy. Worth revisiting only
  if this grows past a POC.
- BigQuery/Vertex AI IAM (service accounts for the agents, dataset-level
  grants) isn't part of this CI/CD setup — that's Phase 5 governance work,
  scoped in `gcp_strategy.md`.
