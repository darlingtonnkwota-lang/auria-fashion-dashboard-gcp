import type { Metadata } from "next";
import "./globals.css";

// System font stack (see globals.css's body rule) rather than
// next/font/google -- deliberately no external network dependency at
// Docker build time (Cloud Build workers, and this repo's own sandboxed
// dev shell, shouldn't need to reach fonts.googleapis.com just to
// build).
export const metadata: Metadata = {
  title: "Auria Fashion Group — Sales Dashboard",
  description: "Client demo POC: agentic analytics over a BigQuery + Vertex AI (Gemini) medallion architecture.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
