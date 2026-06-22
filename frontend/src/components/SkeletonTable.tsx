export default function SkeletonTable({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="section-card" style={{ overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid #e8e8ed" }}>
        <div className="skeleton skeleton-row w-40" />
      </div>
      <div style={{ padding: "12px 16px" }}>
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4" style={{ padding: "8px 0", borderBottom: r < rows - 1 ? "1px solid #f5f5f7" : "none" }}>
            {Array.from({ length: cols }).map((_, c) => (
              <div key={c} className="skeleton" style={{ height: 16, flex: 1, borderRadius: 4 }} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonMetrics({ count = 4 }: { count?: number }) {
  return (
    <div className="metrics">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="metric-card">
          <div className="skeleton skeleton-row w-40" />
          <div className="skeleton skeleton-row w-60" style={{ marginTop: 8 }} />
        </div>
      ))}
    </div>
  );
}
