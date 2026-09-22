import Card, { CardLoading, CardEmpty } from "./Card";
import { SupplierPerformanceRow } from "@/lib/types";

interface Props {
  data: SupplierPerformanceRow[];
  loading: boolean;
}

export default function SupplierPerformanceTable({ data, loading }: Props) {
  if (loading) {
    return (
      <Card title="Supplier Lead Time & Reliability" eyebrow="All time">
        <CardLoading />
      </Card>
    );
  }
  if (data.length === 0) {
    return (
      <Card title="Supplier Lead Time & Reliability" eyebrow="All time">
        <CardEmpty />
      </Card>
    );
  }

  return (
    <Card title="Supplier Lead Time & Reliability" eyebrow="All time">
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Avg Lead Time</th>
              <th>Stated</th>
              <th>% Late</th>
              <th>Reliability</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r) => (
              <tr key={r.supplier_id}>
                <td>{r.supplier_name}</td>
                <td>{r.avg_actual_lead_time_days.toFixed(1)}d</td>
                <td>{r.stated_avg_lead_time_days.toFixed(1)}d</td>
                <td>
                  <span className={`pill ${r.pct_late > 15 ? "pill-late" : "pill-ontime"}`}>
                    {r.pct_late.toFixed(1)}%
                  </span>
                </td>
                <td>{r.reliability_score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
