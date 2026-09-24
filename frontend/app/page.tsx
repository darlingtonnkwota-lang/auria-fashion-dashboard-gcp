"use client";

import { useEffect, useState } from "react";
import FilterBar from "@/components/FilterBar";
import ChatSidebar from "@/components/ChatSidebar";
import KpiCards from "@/components/KpiCards";
import RevenueForecastChart from "@/components/RevenueForecastChart";
import OrdersForecastChart from "@/components/OrdersForecastChart";
import MarginReturnChart from "@/components/MarginReturnChart";
import ChannelPerformanceChart from "@/components/ChannelPerformanceChart";
import ProductPerformanceScatter from "@/components/ProductPerformanceScatter";
import TopProductsTable from "@/components/TopProductsTable";
import TopCustomersTable from "@/components/TopCustomersTable";
import SupplierPerformanceTable from "@/components/SupplierPerformanceTable";
import {
  EMPTY_FILTERS,
  Filters,
  MonthlyKpiRow,
  YtdRow,
  ForecastRow,
  TopProductRow,
  TopCustomerRow,
  ChannelPerformanceRow,
  SupplierPerformanceRow,
  ProductPerformanceRow,
} from "@/lib/types";

// Phase 7 -- the dashboard is now fully native (Recharts components
// below, fed by app/main.py's /api/dashboard/* endpoints), not an
// embedded Looker Studio report. See gcp_strategy.md section 7 for why,
// and docs/gcp_phase7_dashboard_frontend_setup.md for what's filter-
// scoped vs. not yet (the FilterBar still drives the chat sidebar fully;
// the tiles themselves are a named, not-yet-wired simplification).

interface DashboardData {
  monthlyKpis: MonthlyKpiRow[];
  ytd: YtdRow[];
  forecast: ForecastRow[];
  topProducts: TopProductRow[];
  topCustomers: TopCustomerRow[];
  channelPerformance: ChannelPerformanceRow[];
  supplierPerformance: SupplierPerformanceRow[];
  productPerformance: ProductPerformanceRow[];
}

const EMPTY_DATA: DashboardData = {
  monthlyKpis: [],
  ytd: [],
  forecast: [],
  topProducts: [],
  topCustomers: [],
  channelPerformance: [],
  supplierPerformance: [],
  productPerformance: [],
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export default function Home() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [data, setData] = useState<DashboardData>(EMPTY_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [monthlyKpis, ytd, forecast, topProducts, topCustomers, channelPerformance, supplierPerformance, productPerformance] =
          await Promise.all([
            getJson<MonthlyKpiRow[]>("/api/dashboard/monthly-kpis"),
            getJson<YtdRow[]>("/api/dashboard/ytd"),
            getJson<ForecastRow[]>("/api/dashboard/forecast"),
            getJson<TopProductRow[]>("/api/dashboard/top-products"),
            getJson<TopCustomerRow[]>("/api/dashboard/top-customers"),
            getJson<ChannelPerformanceRow[]>("/api/dashboard/channel-performance"),
            getJson<SupplierPerformanceRow[]>("/api/dashboard/supplier-performance"),
            getJson<ProductPerformanceRow[]>("/api/dashboard/product-performance"),
          ]);
        if (!cancelled) {
          setData({ monthlyKpis, ytd, forecast, topProducts, topCustomers, channelPerformance, supplierPerformance, productPerformance });
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <h1>Auria Fashion Group</h1>
          <p className="page-subtitle">Global fashion retail — sales &amp; operations</p>
        </div>
        <div className="page-header-badge">
          <span className="pulse-dot" />
          BigQuery + Vertex AI (Gemini)
        </div>
      </header>

      <FilterBar filters={filters} onChange={setFilters} />

      {error && <div className="chat-error">Couldn&apos;t load dashboard data: {error}</div>}

      <div className="page-body">
        <div className="dashboard-area">
          <KpiCards ytd={data.ytd} monthlyKpis={data.monthlyKpis} />

          <div className="chart-grid">
            <RevenueForecastChart monthlyKpis={data.monthlyKpis} forecast={data.forecast} loading={loading} />
            <OrdersForecastChart monthlyKpis={data.monthlyKpis} forecast={data.forecast} loading={loading} />
            <MarginReturnChart monthlyKpis={data.monthlyKpis} loading={loading} />
            <ChannelPerformanceChart data={data.channelPerformance} loading={loading} />
            <ProductPerformanceScatter data={data.productPerformance} loading={loading} />
            <TopProductsTable data={data.topProducts} loading={loading} />
            <TopCustomersTable data={data.topCustomers} loading={loading} />
            <SupplierPerformanceTable data={data.supplierPerformance} loading={loading} />
          </div>
        </div>

        <aside className="sidebar-area">
          <ChatSidebar filters={filters} />
        </aside>
      </div>

      <p className="page-footer">Auria Fashion Group · GCP demo build · Powered by BigQuery, BigQuery ML &amp; Vertex AI</p>
    </main>
  );
}
