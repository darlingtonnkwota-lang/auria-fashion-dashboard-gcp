"use client";

import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Card, { CardLoading, CardEmpty } from "./Card";
import { MonthlyKpiRow, ForecastRow } from "@/lib/types";
import { palette, CHART_TOOLTIP_STYLE } from "@/lib/palette";

interface Props {
  monthlyKpis: MonthlyKpiRow[];
  forecast: ForecastRow[];
  loading: boolean;
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

// Same ARIMA_PLUS output as RevenueForecastChart, just the other metric
// gold_sales_forecast carries (metric = 'order_count') -- history (last
// 18 months) into a 6-month forecast with its 90% prediction interval
// shaded behind it. Deliberately reuses the exact same color language
// (cyan = actual, dashed purple = forecast, translucent purple = band)
// as the revenue chart, so the two tiles read as one pattern rather
// than two unrelated charts that happen to sit next to each other.
export default function OrdersForecastChart({ monthlyKpis, forecast, loading }: Props) {
  if (loading) {
    return (
      <Card title="Orders: history + 6-month forecast" eyebrow="ARIMA_PLUS · 90% interval">
        <CardLoading />
      </Card>
    );
  }

  const history = [...monthlyKpis]
    .sort((a, b) => a.year * 12 + a.month - (b.year * 12 + b.month))
    .slice(-18);
  const forecastRows = forecast
    .filter((f) => f.metric === "order_count" && f.is_forecast)
    .sort((a, b) => a.month_date.localeCompare(b.month_date));

  if (history.length === 0) {
    return (
      <Card title="Orders: history + 6-month forecast" eyebrow="ARIMA_PLUS · 90% interval">
        <CardEmpty />
      </Card>
    );
  }

  type Point = {
    month: string;
    actual: number | null;
    forecastLine: number | null;
    bandBase: number | null;
    bandHeight: number | null;
  };

  const historyPoints: Point[] = history.map((r) => ({
    month: `${r.year}-${pad(r.month)}`,
    actual: r.order_count,
    forecastLine: null,
    bandBase: null,
    bandHeight: null,
  }));

  const forecastPoints: Point[] = forecastRows.map((f) => {
    const lower = f.lower_bound ?? f.value;
    const upper = f.upper_bound ?? f.value;
    return {
      month: f.month_date.slice(0, 7),
      actual: null,
      forecastLine: f.value,
      bandBase: lower,
      bandHeight: upper - lower,
    };
  });

  const merged = [...historyPoints, ...forecastPoints];
  // Bridge the last actual point into the forecast line so the two
  // series connect visually instead of showing a gap.
  if (historyPoints.length > 0 && forecastPoints.length > 0) {
    merged[historyPoints.length - 1] = {
      ...merged[historyPoints.length - 1],
      forecastLine: historyPoints[historyPoints.length - 1].actual,
    };
  }

  return (
    <Card title="Orders: history + 6-month forecast" eyebrow="ARIMA_PLUS · 90% interval">
      <div className="chart-legend">
        <span><i className="legend-swatch" style={{ background: palette.cyan }} /> Actual</span>
        <span><i className="legend-swatch" style={{ background: palette.purple }} /> Forecast</span>
        <span><i className="legend-swatch" style={{ background: "rgba(139,92,246,0.35)" }} /> 90% interval</span>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={merged} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="ordersActualFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={palette.cyan} stopOpacity={0.35} />
              <stop offset="100%" stopColor={palette.cyan} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={palette.grid} vertical={false} />
          <XAxis dataKey="month" stroke={palette.muted} fontSize={11} tickLine={false} axisLine={false} />
          <YAxis
            stroke={palette.muted}
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => Number(v).toLocaleString("en-US")}
            width={56}
          />
          <Tooltip
            contentStyle={CHART_TOOLTIP_STYLE}
            formatter={(value: number, name: string) => {
              if (name === "bandHeight" || name === "bandBase") return [null, null];
              return [Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 }), name === "actual" ? "Actual" : "Forecast"];
            }}
          />
          <Area dataKey="bandBase" stackId="band" stroke="none" fill="transparent" isAnimationActive={false} />
          <Area
            dataKey="bandHeight"
            stackId="band"
            stroke="none"
            fill="rgba(139,92,246,0.22)"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="actual"
            stroke={palette.cyan}
            strokeWidth={2}
            fill="url(#ordersActualFill)"
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecastLine"
            stroke={palette.purple}
            strokeWidth={2.5}
            strokeDasharray="6 4"
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  );
}
