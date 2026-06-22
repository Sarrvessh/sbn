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

function SpanRow({ item, depth, maxDuration }: { item: SpanTreeItem; depth: number; maxDuration: number }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = item.children.length > 0;
  const barWidth = maxDuration > 0 ? (item.duration_ms / maxDuration) * 100 : 0;

  return (
    <div>
      <div
        className="flex items-center gap-2"
        style={{ padding: "7px 0", fontSize: 13, marginLeft: depth * 20 }}
      >
        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          style={{ background: "none", border: "none", cursor: "pointer", padding: 0, width: 16, display: "flex", alignItems: "center", color: "#aeaeb2" }}
        >
          {hasChildren ? (expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />) : <span style={{ width: 13 }} />}
        </button>

        <span className="badge blue" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>{item.span.span_type}</span>
        <span className="truncate" style={{ color: "#1d1d1f", minWidth: 100, fontWeight: 500 }}>{item.span.name}</span>

        <div className="flex-1" style={{ height: 6, background: "#f2f2f7", borderRadius: 3, minWidth: 60 }}>
          <div style={{ width: `${Math.max(barWidth, 2)}%`, height: "100%", background: "#0071e3", borderRadius: 3 }} />
        </div>

        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6e6e73", width: 60, textAlign: "right" }}>
          {item.duration_ms != null && !isNaN(item.duration_ms) ? item.duration_ms.toFixed(1) : "0.0"}ms
        </span>
        {item.span.total_tokens > 0 && (
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6e6e73", width: 50, textAlign: "right" }}>
            {item.span.total_tokens}t
          </span>
        )}
        <span className={`status-label ${item.span.status_code === "OK" ? "green" : "red"}`} style={{ fontSize: 11 }}>
          <span className={`status-dot ${item.span.status_code === "OK" ? "green" : "red"}`} />
          {item.span.status_code}
        </span>
      </div>

      {(item.span.model_name || item.span.tool_name) && (
        <div style={{ marginLeft: 20 + depth * 20, marginBottom: 4, fontSize: 12, color: "#6e6e73", lineHeight: 1.6 }}>
          {item.span.model_name && <div><span style={{ color: "#aeaeb2" }}>model</span> {item.span.model_name}</div>}
          {item.span.tool_name && <div><span style={{ color: "#aeaeb2" }}>tool</span> {item.span.tool_name}</div>}
        </div>
      )}

      {item.span.input && (
        <div style={{ marginLeft: 20 + depth * 20, marginBottom: 4 }}>
          <div style={{ color: "#aeaeb2", fontSize: 11, marginBottom: 2 }}>input</div>
          <pre className="code-block" style={{ maxHeight: 80, overflow: "auto", fontSize: 11 }}>{item.span.input}</pre>
        </div>
      )}
      {item.span.output && (
        <div style={{ marginLeft: 20 + depth * 20, marginBottom: 8 }}>
          <div style={{ color: "#aeaeb2", fontSize: 11, marginBottom: 2 }}>output</div>
          <pre className="code-block" style={{ maxHeight: 80, overflow: "auto", fontSize: 11 }}>{item.span.output}</pre>
        </div>
      )}

      {hasChildren && expanded && item.children.map((child) => (
        <SpanRow key={child.span.span_id} item={child} depth={depth + 1} maxDuration={maxDuration} />
      ))}
    </div>
  );
}

export default function SpanWaterfall({ spans, loading }: { spans: SpanTreeItem[]; loading?: boolean }) {
  if (loading) return <div style={{ fontSize: 13, color: "#6e6e73", padding: "12px 0" }}>Loading spans…</div>;
  if (!spans || spans.length === 0) return <div style={{ fontSize: 13, color: "#aeaeb2", padding: "12px 0" }}>No spans recorded.</div>;

  const maxDuration = Math.max(...spans.map((s) => s.duration_ms || 0), 1);

  return (
    <div className="section-card" style={{ marginBottom: 0 }}>
      <div className="section-card-header">
        <div className="section-card-title">Span Timeline</div>
      </div>
      <div className="section-card-body" style={{ paddingTop: 0 }}>
        {spans.map((s) => (
          <SpanRow key={s.span.span_id} item={s} depth={0} maxDuration={maxDuration} />
        ))}
      </div>
    </div>
  );
}
