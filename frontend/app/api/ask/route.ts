// Server-side proxy to the FastAPI backend's POST /api/ask. Runs on the
// server (Cloud Run), so BACKEND_URL is a plain runtime env var -- never
// exposed to the browser, and never baked into the client bundle the
// way a NEXT_PUBLIC_* variable would be. See cloudbuild.yaml's
// deploy-frontend step for where BACKEND_URL actually gets set.

import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const body = await req.text();

  try {
    const res = await fetch(`${backendUrl}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return NextResponse.json(
      { detail: `Could not reach backend: ${err instanceof Error ? err.message : String(err)}` },
      { status: 502 }
    );
  }
}
