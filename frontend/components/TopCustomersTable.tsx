import Card, { CardLoading, CardEmpty } from "./Card";
import { TopCustomerRow } from "@/lib/types";

interface Props {
  data: TopCustomerRow[];
  loading: boolean;
}

export default function TopCustomersTable({ data, loading }: Props) {
  if (loading) {
    return (
      <Card title="Top 10 Customers by Lifetime Spend" eyebrow="All time">
        <CardLoading />
      </Card>
    );
  }
  if (data.length === 0) {
    return (
      <Card title="Top 10 Customers by Lifetime Spend" eyebrow="All time">
        <CardEmpty />
      </Card>
    );
  }

  return (
    <Card title="Top 10 Customers by Lifetime Spend" eyebrow="All time">
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Customer</th>
              <th>Region</th>
              <th>Lifetime Spend</th>
              <th>Orders</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((r) => (
              <tr key={r.customer_id}>
                <td>{r.first_name} {r.last_name}</td>
                <td>{r.region}</td>
                <td>${r.lifetime_value_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}</td>
                <td>{r.order_count}</td>
                <td>
                  <span className={`pill ${r.order_count > 1 ? "pill-repeat" : "pill-onetime"}`}>
                    {r.order_count > 1 ? "Repeat" : "One-time"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
