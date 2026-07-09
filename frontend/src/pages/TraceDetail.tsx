import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTraceDetail, flagTrace, unflagTrace } from "../lib/api";
import { formatTime, formatCost, formatLatency } from "../lib/utils";
import SpanWaterfall from "../components/SpanWaterfall";
import type { SpanTreeItem } from "../components/SpanWaterfall";
import { ArrowLeft, Shield } from "lucide-react";

function buildTree(spans: SpanTreeItem["span"][]): SpanTreeItem[] {
  const map = new Map<string, SpanTreeItem>();
  const roots: SpanTreeItem[] = [];
  const sorted = [...spans].sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime());
  for (const s of sorted) {
    map.set(s.span_id, { span: s, children: [], duration_ms: s.ended_at ? new Date(s.ended_at).getTime() - new Date(s.started_at).getTime() : 0 });
  }
  for (const item of map.values()) {
    if (item.span.parent_span_id && map.has(item.span.parent_span_id)) {
      map.get(item.span.parent_span_id)!.children.push(item);
    } else { roots.push(item); }
  }
  return roots;
}

export default function TraceDetail() {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [redact, setRedact] = useState(false);
  const id = requestId || "";

  const { data, isLoading } = useQuery({
    queryKey: ["trace", id, redact],
    queryFn: () => fetchTraceDetail(id, redact),
    enabled: !!id,
  });

  const [flagError, setFlagError] = useState<string | null>(null);
  const flagMut = useMutation({
    mutationFn: (flag: boolean) => flag ? flagTrace(id) : unflagTrace(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trace", id] });
      queryClient.invalidateQueries({ queryKey: ["traces"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-traces"] });
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
    },
    onError: (err) => { setFlagError(String(err)); setTimeout(() => setFlagError(null), 3000); },
  });

  if (isLoading) return <div className="page"><div style={{ fontSize: 13, color: "#6e6e73" }}>Loading trace…</div></div>;
  if (!data) return <div className="page"><div style={{ fontSize: 13, color: "#ff3b30" }}>Trace not found.</div></div>;

  const spans: SpanTreeItem["span"][] = (data.spans || []).map((s: Record<string, unknown>) => ({
    span_id: s.span_id as string, parent_span_id: (s.parent_span_id as string | null) || null,
    name: s.name as string, span_type: s.span_type as string, status_code: s.status_code as string,
    total_tokens: (s.total_tokens as number) || 0, cost: (s.cost as number) || 0,
    input: (s.input as string | null) || null, output: (s.output as string | null) || null,
    tool_name: (s.tool_name as string | null) || null, model_name: (s.model_name as string | null) || null,
    started_at: s.started_at as string, ended_at: s.ended_at as string,
  }));
  const tree = buildTree(spans);
  const retrievalDocs = (data.spans || []).flatMap((s) => s.retrieval_documents || []);

  return (
    <div className="page">
      <button onClick={() => navigate(-1)} className="link" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
        <ArrowLeft size={14} /> Back
      </button>

      <div className="flex items-start justify-between" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="page-title" style={{ fontSize: 24, wordBreak: "break-all" }}>{data.request_id}</h1>
          <p style={{ fontSize: 12, color: "#6e6e73", marginTop: 2 }}>{data.project_name} &middot; {data.model_name}</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5" style={{ fontSize: 12, color: "#6e6e73", cursor: "pointer" }}>
            <input type="checkbox" checked={redact} onChange={(e) => setRedact(e.target.checked)} style={{ accentColor: "#0071e3" }} />
            Redact PII
          </label>
          {data.flagged_for_governance && (
            <span className="status-label orange">
              <span className="status-dot orange" />Flagged
            </span>
          )}
          <button
            onClick={() => flagMut.mutate(!data.flagged_for_governance)}
            disabled={flagMut.isPending}
            className={`btn ${data.flagged_for_governance ? "btn-secondary" : "btn-primary"} btn-sm`}
            style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}
          >
            <Shield size={12} />
            {flagMut.isPending ? "..." : data.flagged_for_governance ? "Unflag" : "Flag for Review"}
          </button>
          {flagError && <span style={{ fontSize: 11, color: "#ff3b30" }}>{flagError}</span>}
          <span className={`status-label ${data.status === "success" ? "green" : "red"}`}>
            <span className={`status-dot ${data.status === "success" ? "green" : "red"}`} />{data.status}
          </span>
        </div>
      </div>

      <div className="metrics" style={{ marginBottom: 24, gridTemplateColumns: "repeat(4, 1fr)" }}>
        <div className="metric-card"><div className="metric-label">Timestamp</div><div className="metric-value" style={{ fontSize: 14, fontFamily: "'Inter', sans-serif" }}>{formatTime(data.timestamp)}</div></div>
        <div className="metric-card"><div className="metric-label">Latency</div><div className="metric-value" style={{ fontSize: 14 }}>{formatLatency(data.latency_ms)}</div></div>
        <div className="metric-card"><div className="metric-label">Tokens</div><div className="metric-value" style={{ fontSize: 14 }}>{data.total_tokens}</div></div>
        <div className="metric-card"><div className="metric-label">Cost</div><div className="metric-value" style={{ fontSize: 14 }}>{formatCost(data.cost)}</div></div>
      </div>

      <div className="section-card" style={{ marginBottom: 16 }}>
        <div className="section-card-header">
          <div className="section-card-title">Prompt & Response</div>
        </div>
        <div className="section-card-body">
          <div style={{ marginBottom: 12 }}>
            <div style={{ color: "#aeaeb2", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Prompt</div>
            <div className="code-block" style={{ fontSize: 12, maxHeight: 150, overflow: "auto", whiteSpace: "pre-wrap" }}>{data.prompt}</div>
          </div>
          <div>
            <div style={{ color: "#aeaeb2", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Response</div>
            <div className="code-block" style={{ fontSize: 12, maxHeight: 150, overflow: "auto", whiteSpace: "pre-wrap" }}>{data.response}</div>
          </div>
        </div>
      </div>

      <SpanWaterfall spans={tree} />

      {retrievalDocs.length > 0 && (
        <div className="section-card" style={{ marginTop: 16 }}>
          <div className="section-card-header">
            <div className="section-card-title">RAG Documents ({retrievalDocs.length})</div>
          </div>
          <div className="section-card-body" style={{ paddingTop: 0 }}>
            {retrievalDocs.map((d: { id: string; content: string; score: number; source: string }) => (
              <div key={d.id} className="flex items-start gap-3" style={{ padding: "10px 0", borderBottom: "1px solid #e8e8ed" }}>
                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-2" style={{ marginBottom: 2 }}>
                    <span className="badge blue" style={{ fontSize: 10 }}>{d.id}</span>
                    <span className="badge">score: {d.score != null ? d.score.toFixed(3) : "N/A"}</span>
                    <span className="badge">{d.source}</span>
                  </div>
                  <div style={{ fontSize: 12, color: "#6e6e73" }}>{d.content}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
