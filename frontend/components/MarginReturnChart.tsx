"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Card, { CardLoading, CardEmpty } from "./Card";
import { MonthlyKpiRow } from "@/lib/types";
import { palette, CHART_TOOLTIP_STYLE } from "@/lib/palette";

interface Props {
  monthlyKpis: MonthlyKpiRow[];
  loading: boolean;
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

export default function MarginReturnChart({ monthlyKpis, loading }: Props) {
  if (loading) {
    return (
      <Card title="Margin % vs. Return Rate %" eyebrow="gold_monthly_kpis">
        <CardLoading />
      </Card>
    );
  }
  if (monthlyKpis.length === 0) {
    return (
      <Card title="Margin % vs. Return Rate %" eyebrow="gold_monthly_kpis">
        <CardEmpty />
      </Card>
    );
  }

  const data = [...monthlyKpis]
    .sort((a, b) => a.year * 12 + a.month - (b.year * 12 + b.month))
    .map((r) => ({
      month: `${r.year}-${pad(r.month)}`,
      margin_pct: r.margin_pct,
      return_rate_pct: r.return_rate_pct,
    }));

  return (
    <Card title="Margin % vs. Return Rate %" eyebrow="gold_monthly_kpis">
      <div className="chart-legend">
        <span><i className="legend-swatch" style={{ background: palette.emerald }} /> Margin %</span>
        <span><i className="legend-swatch" style={{ background: palette.rose }} /> Return Rate %</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={palette.grid} vertical={false} />
          <XAxis dataKey="month" stroke={palette.muted} fontSize={11} tickLine={false} axisLine={false} />
          <YAxis
            yAxisId="margin"
            stroke={palette.muted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={44}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            yAxisId="return"
            orientation="right"
            stroke={palette.muted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={40}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(v: number) => `${Number(v).toFixed(1)}%`} />
          <Line yAxisId="margin" type="monotone" dataKey="margin_pct" stroke={palette.emerald} strokeWidth={2} dot={false} />
          <Line yAxisId="return" type="monotone" dataKey="return_rate_pct" stroke={palette.rose} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
