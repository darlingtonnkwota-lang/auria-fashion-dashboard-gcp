/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Phase 7 -- runs as its own Cloud Run service (frontend/Dockerfile's
  // multi-stage build copies .next/standalone), not on Vercel like the
  // Databricks build's frontend.
  output: "standalone",
};

export default nextConfig;
