"""Walking-skeleton service for the Auria GCP backend.

Purpose: prove the repo -> Cloud Build -> Cloud Run pipeline works end to
end (dev branch -> dev service, main branch -> prod service) *before* any
real BigQuery/agent logic exists. Once Phase 5's agent code lands, this
file becomes the real FastAPI app (mirroring backend/main.py in the
Databricks build) rather than a separate throwaway.
"""
from fastapi import FastAPI

app = FastAPI(title="Auria Fashion Group — GCP backend")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "auria-backend"}


@app.get("/")
def root():
    return {"message": "Auria Fashion Group GCP backend — walking skeleton"}
