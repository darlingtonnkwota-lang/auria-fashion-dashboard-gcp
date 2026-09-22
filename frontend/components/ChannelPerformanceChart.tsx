"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import Card, { CardLoading, CardEmpty } from "./Card";
import { ChannelPerformanceRow } from "@/lib/types";
import { palette, CHART_TOOLTIP_STYLE } from "@/lib/palette";

interface Props {
  data: ChannelPerformanceRow[];
  loading: boolean;
}

export default function ChannelPerformanceChart({ data, loading }: Props) {
  if (loading) {
    return (
      <Card title="Online vs. In-Store Revenue by Year" eyebrow="gold_channel_performance">
        <CardLoading />
      </Card>
    );
  }
  if (data.length === 0) {
    return (
      <Card title="Online vs. In-Store Revenue by Year" eyebrow="gold_channel_performance">
        <CardEmpty />
      </Card>
    );
  }

  const years = Array.from(new Set(data.map((r) => r.year))).sort();
  const chartData = years.map((year) => {
    const row: Record<string, number | string> = { year };
    data
      .filter((r) => r.year === year)
      .forEach((r) => {
        row[r.channel] = r.revenue_usd;
      });
    return row;
  });
  const channels = Array.from(new Set(data.map((r) => r.channel)));
  const colors = [palette.cyan, palette.amber, palette.purple];

  return (
    <Card title="Online vs. In-Store Revenue by Year" eyebrow="gold_channel_performance">
      <div className="chart-legend">
        {channels.map((c, i) => (
          <span key={c}><i className="legend-swatch" style={{ background: colors[i % colors.length] }} /> {c}</span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={palette.grid} vertical={false} />
          <XAxis dataKey="year" stroke={palette.muted} fontSize={11} tickLine={false} axisLine={false} />
          <YAxis
            stroke={palette.muted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
          />
          <Tooltip
            contentStyle={CHART_TOOLTIP_STYLE}
            formatter={(v: number) => `$${Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 })}`}
          />
          {channels.map((c, i) => (
            <Bar key={c} dataKey={c} fill={colors[i % colors.length]} radius={[6, 6, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
