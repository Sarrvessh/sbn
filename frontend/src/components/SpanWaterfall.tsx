import { useState } from "react";
import { ChevronRight, ChevronDown } from "lucide-react";

export interface SpanTreeItem {
  span: {
    span_id: string;
    parent_span_id: string | null;
    name: string;
    span_type: string;
    status_code: string;
    total_tokens: number;
    cost: number;
    input: string | null;
    output: string | null;
    tool_name: string | null;
    model_name: string | null;
    started_at: string;
    ended_at: string;
  };
  children: SpanTreeItem[];
  duration_ms: number;
}

const TYPE_COLORS: Record<string, string> = {
  llm: "blue",
  tool: "purple",
  retrieval: "orange",
  chain: "",
};

function SpanRow({ item, depth, maxDuration }: { item: SpanTreeItem; depth: number; maxDuration: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = item.children.length > 0;
  const barWidth = maxDuration > 0 ? (item.duration_ms / maxDuration) * 100 : 0;
  const ok = item.span.status_code === "OK";
  const typeColor = TYPE_COLORS[item.span.span_type] ?? "blue";

  return (
    <div>
      <div
        className="flex items-center gap-2"
        style={{ padding: "8px 0", fontSize: 13, marginLeft: depth * 22 }}
      >
        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          aria-label={expanded ? "Collapse span" : "Expand span"}
          style={{
            background: "none", border: "none", cursor: "pointer", padding: 2,
            width: 18, height: 18, display: "flex", alignItems: "center", justifyContent: "center",
            color: "var(--label-3)", borderRadius: 4,
            transition: "transform 180ms var(--ease-out), color 120ms ease",
          }}
        >
          {hasChildren ? (expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />) : <span style={{ width: 14 }} />}
        </button>

        <span className={`badge ${typeColor}`} style={{ fontFamily: "var(--font-mono)", fontSize: 10 }}>
          {item.span.span_type}
        </span>
        <span className="truncate" style={{ color: "var(--label-1)", minWidth: 100, fontWeight: 500 }}>{item.span.name}</span>

        <div className="flex-1" style={{ height: 6, background: "var(--fill-2)", borderRadius: 3, minWidth: 60, overflow: "hidden" }}>
          <div
            style={{
              width: `${Math.max(barWidth, 2.5)}%`, height: "100%", borderRadius: 3,
              background: ok
                ? "linear-gradient(90deg, rgba(23,131,255,0.55), var(--accent))"
                : "linear-gradient(90deg, rgba(255,56,73,0.55), var(--red))",
              transition: "width 300ms var(--ease-out)",
            }}
          />
        </div>

        <span className="text-mono" style={{ fontSize: 11, color: "var(--label-2)", width: 64, textAlign: "right", flexShrink: 0 }}>
          {item.duration_ms != null && !isNaN(item.duration_ms) ? item.duration_ms.toFixed(1) : "0.0"}ms
        </span>
        {item.span.total_tokens > 0 && (
          <span className="text-mono" style={{ fontSize: 11, color: "var(--label-3)", width: 52, textAlign: "right", flexShrink: 0 }}>
            {item.span.total_tokens}t
          </span>
        )}
        <span className={`status-label ${ok ? "green" : "red"}`} style={{ fontSize: 11, width: 56, flexShrink: 0 }}>
          <span className={`status-dot ${ok ? "green" : "red"}`} />
          {item.span.status_code}
        </span>
      </div>

      {(item.span.model_name || item.span.tool_name) && (
        <div style={{ marginLeft: 22 + depth * 22, marginBottom: 4, fontSize: 12, color: "var(--label-2)", lineHeight: 1.6 }}>
          {item.span.model_name && <div><span style={{ color: "var(--label-3)" }}>model</span>&ensp;{item.span.model_name}</div>}
          {item.span.tool_name && <div><span style={{ color: "var(--label-3)" }}>tool</span>&ensp;{item.span.tool_name}</div>}
        </div>
      )}

      {item.span.input && (
        <div style={{ marginLeft: 22 + depth * 22, marginBottom: 6 }}>
          <div style={{ color: "var(--label-3)", fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>Input</div>
          <pre className="code-block" style={{ maxHeight: 120, overflow: "auto", fontSize: 11, margin: 0 }}>{item.span.input}</pre>
        </div>
      )}
      {item.span.output && (
        <div style={{ marginLeft: 22 + depth * 22, marginBottom: 8 }}>
          <div style={{ color: "var(--label-3)", fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>Output</div>
          <pre className="code-block" style={{ maxHeight: 120, overflow: "auto", fontSize: 11, margin: 0 }}>{item.span.output}</pre>
        </div>
      )}

      {hasChildren && expanded && item.children.map((child) => (
        <SpanRow key={child.span.span_id} item={child} depth={depth + 1} maxDuration={maxDuration} />
      ))}
    </div>
  );
}

export default function SpanWaterfall({ spans, loading }: { spans: SpanTreeItem[]; loading?: boolean }) {
  if (loading) return <div style={{ fontSize: 13, color: "var(--label-2)", padding: "12px 0" }}>Loading spans…</div>;
  if (!spans || spans.length === 0) return <div style={{ fontSize: 13, color: "var(--label-3)", padding: "12px 0" }}>No spans recorded.</div>;

  const maxDuration = Math.max(...spans.map((s) => s.duration_ms || 0), 1);

  return (
    <div className="section-card" style={{ marginBottom: 0 }}>
      <div className="section-card-header">
        <div className="section-card-title">Span Timeline</div>
        <span style={{ fontSize: 11, color: "var(--label-3)" }}>{spans.length} root span{spans.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="section-card-body" style={{ paddingTop: 0 }}>
        {spans.map((s) => (
          <SpanRow key={s.span.span_id} item={s} depth={0} maxDuration={maxDuration} />
        ))}
      </div>
    </div>
  );
}
