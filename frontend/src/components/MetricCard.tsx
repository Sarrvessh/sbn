interface MetricCardProps {
  label: string;
  value: string;
  subtitle?: string;
  accent?: boolean;
  green?: boolean;
  red?: boolean;
}

export default function MetricCard({ label, value, subtitle, accent, green, red }: MetricCardProps) {
  const cls = accent ? "accent" : green ? "green" : red ? "red" : "";
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${cls}`}>{value}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  );
}
