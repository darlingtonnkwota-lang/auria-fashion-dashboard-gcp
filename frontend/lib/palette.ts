// Single source of truth for chart colors -- kept in sync with
// app/globals.css's CSS variables so every chart, KPI card, and the
// chrome around them read as one system. Recharts needs real hex/rgba
// strings (it can't read CSS custom properties), so these are the same
// values duplicated here on purpose, not re-derived at runtime.

export const palette = {
  purple: "#8b5cf6",
  pink: "#ec4899",
  amber: "#f59e0b",
  cyan: "#22d3ee",
  emerald: "#34d399",
  rose: "#fb7185",
  ink: "#f3f3fb",
  muted: "#9797bd",
  grid: "rgba(255,255,255,0.08)",
  surface2: "#191c3a",
};

export const CHART_TOOLTIP_STYLE = {
  background: "#191c3a",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 10,
  color: "#f3f3fb",
  fontSize: 12,
};
