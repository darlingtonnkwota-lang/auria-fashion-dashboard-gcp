import Card, { CardLoading, CardEmpty } from "./Card";
import { TopProductRow } from "@/lib/types";

interface Props {
  data: TopProductRow[];
  loading: boolean;
}

export default function TopProductsTable({ data, loading }: Props) {
  if (loading) {
    return (
      <Card title="Top 5 Products by Revenue" eyebrow="This year">
        <CardLoading />
      </Card>
    );
  }
  if (data.length === 0) {
    return (
      <Card title="Top 5 Products by Revenue" eyebrow="This year">
        <CardEmpty />
      </Card>
    );
  }

  return (
    <Card title="Top 5 Products by Revenue" eyebrow="This year">
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Category</th>
              <th>Revenue</th>
              <th>Units</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r) => (
              <tr key={r.product_id}>
                <td>{r.product_name}</td>
                <td>{r.category}</td>
                <td>${r.revenue_usd.toLocaleString("en-US", { maximumFractionDigits: 0 })}</td>
                <td>{r.units_sold.toLocaleString("en-US")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
