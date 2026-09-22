// Server-side proxy for every GET /api/dashboard/* tile endpoint (see
// app/main.py). One catch-all route so adding a new tile on the backend
// never needs a matching new route file here -- same BACKEND_URL
// runtime env var as app/api/ask/route.ts.

import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
  const { path } = await params;
  const search = req.nextUrl.search;

  try {
    const res = await fetch(`${backendUrl}/api/dashboard/${path.join("/")}${search}`);
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
