import { YtdRow, MonthlyKpiRow } from "@/lib/types";

interface KpiCardsProps {
  ytd: YtdRow[];
  monthlyKpis: MonthlyKpiRow[];
}

function fmtUsd(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
}

function fmtNum(n: number): string {
  return n.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export default function KpiCards({ ytd, monthlyKpis }: KpiCardsProps) {
  if (ytd.length === 0 || monthlyKpis.length === 0) {
    return (
      <div className="kpi-grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="kpi-card">
            <div className="kpi-label">Loading…</div>
          </div>
        ))}
      </div>
    );
  }

  const sorted = [...ytd].sort((a, b) => a.year - b.year);
  const current = sorted[sorted.length - 1];
  const prior = sorted.length > 1 ? sorted[sorted.length - 2] : null;
  const yoyRevenue = prior && prior.revenue_usd > 0
    ? ((current.revenue_usd - prior.revenue_usd) / prior.revenue_usd) * 100
    : null;
  const marginPct = current.revenue_usd > 0 ? (current.margin_usd / current.revenue_usd) * 100 : 0;

  const latestMonth = [...monthlyKpis].sort(
    (a, b) => a.year * 12 + a.month - (b.year * 12 + b.month)
  )[monthlyKpis.length - 1];

  const cards = [
    {
      label: `Revenue YTD (${current.year})`,
      value: fmtUsd(current.revenue_usd),
      delta: yoyRevenue,
      accent: "linear-gradient(135deg, var(--accent-purple), var(--accent-pink))",
    },
    {
      label: "YoY Revenue Growth",
      value: yoyRevenue !== null ? `${yoyRevenue >= 0 ? "+" : ""}${yoyRevenue.toFixed(1)}%` : "—",
      delta: null,
      accent: "linear-gradient(135deg, var(--accent-pink), var(--accent-amber))",
    },
    {
      label: "Orders YTD",
      value: fmtNum(current.order_count),
      delta: null,
      accent: "linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))",
    },
    {
      label: "AOV YTD",
      value: fmtUsd(current.aov_usd),
      delta: null,
      accent: "linear-gradient(135deg, var(--accent-amber), var(--accent-cyan))",
    },
    {
      label: "Margin % YTD",
      value: `${marginPct.toFixed(1)}%`,
      delta: null,
      accent: "linear-gradient(135deg, var(--accent-emerald), var(--accent-cyan))",
    },
    {
      label: `Return Rate % (${latestMonth.year}-${String(latestMonth.month).padStart(2, "0")})`,
      value: `${latestMonth.return_rate_pct.toFixed(1)}%`,
      delta: null,
      accent: "linear-gradient(135deg, var(--accent-rose), var(--accent-pink))",
    },
  ];

  return (
    <div className="kpi-grid">
      {cards.map((c) => (
        <div key={c.label} className="kpi-card" style={{ "--kpi-accent": c.accent } as React.CSSProperties}>
          <div className="kpi-label">{c.label}</div>
          <div className="kpi-value">{c.value}</div>
          {c.delta !== null && (
            <div className={`kpi-delta ${c.delta >= 0 ? "up" : "down"}`}>
              {c.delta >= 0 ? "▲" : "▼"} {Math.abs(c.delta).toFixed(1)}% vs {prior?.year}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
