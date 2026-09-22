import { ReactNode } from "react";

interface CardProps {
  title: string;
  eyebrow?: string;
  accent?: string; // CSS gradient/color for the top accent bar
  children: ReactNode;
}

// Shared shell every dashboard tile renders inside -- keeps the top
// accent stripe, title row, and loading/empty states consistent across
// every chart and table component.
export default function Card({ title, eyebrow, accent, children }: CardProps) {
  return (
    <div className="card" style={accent ? ({ "--card-accent": accent } as React.CSSProperties) : undefined}>
      <div className="card-title">
        <h3>{title}</h3>
        {eyebrow && <span className="card-eyebrow">{eyebrow}</span>}
      </div>
      {children}
    </div>
  );
}

export function CardLoading() {
  return <div className="card-loading">Loading…</div>;
}

export function CardEmpty({ message = "No data yet." }: { message?: string }) {
  return <div className="card-empty">{message}</div>;
}
