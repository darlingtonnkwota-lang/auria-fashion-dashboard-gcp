// Shared types -- filter bar, chat sidebar, and the native dashboard
// tiles' API responses. `Filters` mirrors what
// agents.orchestrator.answer_question's `filters` dict expects on the
// backend (see context/schema_reference.yaml's dimension columns if you
// add more).

export interface Filters {
  region: string; // "" means "all regions"
  channel: string; // "" means "all channels"
  startDate: string; // ISO yyyy-mm-dd, "" means unset
  endDate: string; // ISO yyyy-mm-dd, "" means unset
}

export const EMPTY_FILTERS: Filters = {
  region: "",
  channel: "",
  startDate: "",
  endDate: "",
};

// Mirrors agents.orchestrator.answer_question's return dict exactly --
// see agents/orchestrator.py.
export interface AskResponse {
  question: string;
  filters: Record<string, string>;
  sql: string;
  sql_rationale: string;
  rejected: boolean;
  rejection_reason: string | null;
  rows: Record<string, unknown>[];
  columns: string[];
  answer: string;
}

export interface ChatMessage {
  id: string;
  question: string;
  status: "pending" | "done" | "error";
  response?: AskResponse;
  errorMessage?: string;
}

// --- Native dashboard tile payloads (app/main.py's /api/dashboard/*) ---

export interface MonthlyKpiRow {
  year: number;
  month: number;
  revenue_usd: number;
  order_count: number;
  aov_usd: number;
  units_sold: number;
  margin_usd: number;
  margin_pct: number;
  returns_usd: number;
  return_count: number;
  return_rate_pct: number;
}

export interface YtdRow {
  year: number;
  cutoff_doy: number;
  revenue_usd: number;
  order_count: number;
  aov_usd: number;
  margin_usd: number;
}

export interface ForecastRow {
  metric: "revenue_usd" | "order_count";
  month_date: string;
  value: number;
  lower_bound: number | null;
  upper_bound: number | null;
  is_forecast: boolean;
}

export interface TopProductRow {
  product_id: string;
  product_name: string;
  category: string;
  sub_category: string;
  revenue_usd: number;
  units_sold: number;
  margin_usd: number;
}

export interface TopCustomerRow {
  customer_id: string;
  first_name: string;
  last_name: string;
  region: string;
  lifetime_value_usd: number;
  order_count: number;
}

export interface ReturnsByProductRow {
  product_id: string;
  product_name: string;
  category: string;
  size_range: string;
  return_count: number;
  lines_sold: number;
  return_rate_pct: number;
}

export interface ChannelPerformanceRow {
  year: number;
  channel: string;
  revenue_usd: number;
  order_count: number;
}

export interface SupplierPerformanceRow {
  supplier_id: string;
  supplier_name: string;
  po_count: number;
  avg_actual_lead_time_days: number;
  pct_late: number;
  stated_avg_lead_time_days: number;
  reliability_score: number;
}
