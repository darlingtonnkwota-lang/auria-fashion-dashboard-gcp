"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Card, { CardLoading, CardEmpty } from "./Card";
import { ProductPerformanceRow } from "@/lib/types";
import { palette, CHART_TOOLTIP_STYLE } from "@/lib/palette";

interface Props {
  data: ProductPerformanceRow[];
  loading: boolean;
}

// A diagnostic view, not a leaderboard -- the point is to spot products
// that are BOTH high-volume AND high-return at a glance, which a
// top-5-by-return-rate table can't show (a niche product with a 40%
// return rate on 10 units matters far less than a bestseller with a
// 12% return rate on 3,000 units). X = units sold (all-time), Y =
// return rate %, bubble size = revenue -- so the products worth a
// second look are the big bubbles sitting high on the chart. Colored by
// category (same "one Scatter series per category" pattern
// ChannelPerformanceChart.tsx uses for channel), matching Auria's 6
// product categories from generate_data.py.
const CATEGORY_COLORS: Record<string, string> = {
  Outerwear: palette.purple,
  Tops: palette.cyan,
  Bottoms: palette.amber,
  Dresses: palette.pink,
  Footwear: palette.emerald,
  Accessories: palette.rose,
};
const FALLBACK_COLORS = [palette.purple, palette.cyan, palette.amber, palette.pink, palette.emerald, palette.rose];

export default function ProductPerformanceScatter({ data, loading }: Props) {
  if (loading) {
    return (
      <Card title="Product Performance: Volume vs. Return Rate" eyebrow="lines_sold × return_rate_pct × revenue">
        <CardLoading />
      </Card>
    );
  }
  if (data.length === 0) {
    return (
      <Card title="Product Performance: Volume vs. Return Rate" eyebrow="lines_sold × return_rate_pct × revenue">
        <CardEmpty />
      </Card>
    );
  }

  const categories = Array.from(new Set(data.map((r) => r.category))).sort();
  const colorFor = (category: string, i: number) => CATEGORY_COLORS[category] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length];

  return (
    <Card title="Product Performance: Volume vs. Return Rate" eyebrow="lines_sold × return_rate_pct × revenue">
      <div className="chart-legend">
        {categories.map((c, i) => (
          <span key={c}><i className="legend-swatch" style={{ background: colorFor(c, i) }} /> {c}</span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={palette.grid} />
          <XAxis
            type="number"
            dataKey="lines_sold"
            name="Units sold"
            stroke={palette.muted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            label={{ value: "Units sold (lines)", position: "insideBottom", offset: -4, fill: palette.muted, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="return_rate_pct"
            name="Return rate"
            stroke={palette.muted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={48}
            tickFormatter={(v) => `${v}%`}
          />
          <ZAxis type="number" dataKey="revenue_usd" range={[40, 900]} name="Revenue" />
          <Tooltip
            cursor={{ stroke: palette.grid }}
            contentStyle={CHART_TOOLTIP_STYLE}
            content={({ active, payload }) => {
              if (!active || !payload || payload.length === 0) return null;
              const row = payload[0].payload as ProductPerformanceRow;
              return (
                <div style={{ ...CHART_TOOLTIP_STYLE, padding: "8px 10px", lineHeight: 1.5 }}>
                  <strong>{row.product_name}</strong>
                  <div>{row.category}</div>
                  <div>{row.lines_sold.toLocaleString("en-US")} units sold</div>
                  <div>{Number(row.return_rate_pct).toFixed(1)}% return rate</div>
                  <div>${Number(row.revenue_usd).toLocaleString("en-US", { maximumFractionDigits: 0 })} revenue</div>
                </div>
              );
            }}
          />
          {categories.map((category, i) => (
            <Scatter
              key={category}
              name={category}
              data={data.filter((r) => r.category === category)}
              fill={colorFor(category, i)}
              fillOpacity={0.75}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </Card>
  );
}
