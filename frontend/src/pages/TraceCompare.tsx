import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRecentTraces, fetchTraceDetail } from "../lib/api";
import { formatCost, formatLatency, formatTime } from "../lib/utils";
import { ArrowRight, ArrowLeft, X } from "lucide-react";
import type { RecentTrace, TraceDetail } from "../lib/api";

function diffWords(a: string, b: string): { text: string; added?: boolean; removed?: boolean }[] {
  if (a === b) return [{ text: a }];
  const aWords = a.split(/(\s+)/);
  const bWords = b.split(/(\s+)/);
  const result: { text: string; added?: boolean; removed?: boolean }[] = [];
  const maxLen = Math.max(aWords.length, bWords.length);
  for (let i = 0; i < maxLen; i++) {
    if (i < aWords.length && i < bWords.length) {
      if (aWords[i] === bWords[i]) {
        result.push({ text: aWords[i] });
      } else {
        if (aWords[i]) result.push({ text: aWords[i], removed: true });
        if (bWords[i]) result.push({ text: bWords[i], added: true });
      }
    } else if (i < aWords.length) {
      result.push({ text: aWords[i], removed: true });
    } else if (i < bWords.length) {
      result.push({ text: bWords[i], added: true });
    }
  }
  return result;
}

function DiffText({ text, compareText }: { text: string; compareText?: string }) {
  if (!compareText || text === compareText) return <span style={{ whiteSpace: "pre-wrap" }}>{text}</span>;
  const parts = diffWords(text, compareText);
  return (
    <span style={{ whiteSpace: "pre-wrap" }}>
      {parts.map((p, i) => (
        <span key={i} style={{
          background: p.removed ? "#ffeeee" : p.added ? "#e8fde8" : "transparent",
          textDecoration: p.removed ? "line-through" : "none",
          color: p.removed ? "#ff3b30" : p.added ? "#34c759" : "inherit",
          borderRadius: 2, padding: "0 1px",
        }}>{p.text}</span>
      ))}
    </span>
  );
}

function TracePanel({ trace, compareTrace, label, onRemove }: { trace: TraceDetail; compareTrace?: TraceDetail; label: string; onRemove?: () => void }) {
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600 }}>{label}</h3>
        {onRemove && <button onClick={onRemove} className="btn btn-secondary btn-sm" style={{ padding: "2px 6px" }}><X size={12} /></button>}
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex gap-3" style={{ fontSize: 12 }}>
          <div className="metric-card" style={{ flex: 1, padding: "8px 12px" }}>
            <div className="metric-label">Cost</div>
            <div className="metric-value" style={{ fontSize: 14 }}>{formatCost(trace.cost)}</div>
          </div>
          <div className="metric-card" style={{ flex: 1, padding: "8px 12px" }}>
            <div className="metric-label">Tokens</div>
            <div className="metric-value" style={{ fontSize: 14 }}>{trace.total_tokens}</div>
          </div>
          <div className="metric-card" style={{ flex: 1, padding: "8px 12px" }}>
            <div className="metric-label">Latency</div>
            <div className="metric-value" style={{ fontSize: 14 }}>{formatLatency(trace.latency_ms)}</div>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#aeaeb2", textTransform: "uppercase", marginBottom: 4 }}>Prompt</div>
          <div className="code-block" style={{ fontSize: 12, maxHeight: 150, overflow: "auto", whiteSpace: "pre-wrap" }}>
            <DiffText text={trace.prompt} compareText={compareTrace?.prompt} />
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#aeaeb2", textTransform: "uppercase", marginBottom: 4 }}>Response</div>
          <div className="code-block" style={{ fontSize: 12, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap" }}>
            <DiffText text={trace.response} compareText={compareTrace?.response} />
          </div>
        </div>
        <div style={{ fontSize: 11, color: "#6e6e73" }}>
          <span style={{ fontWeight: 500 }}>{trace.project_name}</span> &middot; {trace.model_name} &middot; <span className={`status-label ${trace.status === "success" ? "green" : "red"}`} style={{ fontSize: 10 }}><span className={`status-dot ${trace.status === "success" ? "green" : "red"}`} />{trace.status}</span>
          {trace.flagged_for_governance && <span className="status-label orange" style={{ marginLeft: 6, fontSize: 10 }}>Flagged</span>}
        </div>
        <div style={{ fontSize: 11, color: "#aeaeb2" }}>{formatTime(trace.timestamp)}</div>
      </div>
    </div>
  );
}

export default function TraceCompare() {
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [search, setSearch] = useState("");

  const { data: allTraces } = useQuery({
    queryKey: ["traces-compare"],
    queryFn: () => fetchRecentTraces(200),
  });

  const { data: leftTrace } = useQuery({
    queryKey: ["trace", leftId, false],
    queryFn: () => fetchTraceDetail(leftId),
    enabled: !!leftId,
  });

  const { data: rightTrace } = useQuery({
    queryKey: ["trace", rightId, false],
    queryFn: () => fetchTraceDetail(rightId),
    enabled: !!rightId,
  });

  const filtered = (allTraces || []).filter((t) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return t.request_id.toLowerCase().includes(q) || t.project_name.toLowerCase().includes(q);
  });

  return (
    <div className="page">
      <h1 className="page-title" style={{ marginBottom: 4 }}>Trace Comparison</h1>
      <p className="page-subtitle">Select two traces to compare side by side</p>

      <div className="section-card" style={{ marginBottom: 16 }}>
        <div className="section-card-body">
          <div className="flex gap-3" style={{ marginBottom: 8 }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Trace A</label>
              <select value={leftId} onChange={(e) => setLeftId(e.target.value)} className="input" style={{ width: "100%", fontSize: 12 }}>
                <option value="">Select trace…</option>
                {(search ? filtered : allTraces || []).map((t) => <option key={t.request_id} value={t.request_id}>{t.request_id.slice(0, 16)}… ({t.project_name})</option>)}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Trace B</label>
              <select value={rightId} onChange={(e) => setRightId(e.target.value)} className="input" style={{ width: "100%", fontSize: 12 }}>
                <option value="">Select trace…</option>
                {(search ? filtered : allTraces || []).map((t) => <option key={t.request_id} value={t.request_id}>{t.request_id.slice(0, 16)}… ({t.project_name})</option>)}
              </select>
            </div>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Search traces</label>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by ID or project…" className="input" style={{ width: "100%", fontSize: 12 }} />
          </div>
        </div>
      </div>

      {leftTrace && rightTrace ? (
        <div className="flex gap-4" style={{ alignItems: "flex-start" }}>
          <TracePanel trace={leftTrace} compareTrace={rightTrace} label="Trace A" onRemove={() => setLeftId("")} />
          <div style={{ padding: "40px 8px 0", color: "#aeaeb2" }}>
            <ArrowRight size={20} />
            <ArrowLeft size={20} style={{ marginTop: -8 }} />
          </div>
          <TracePanel trace={rightTrace} compareTrace={leftTrace} label="Trace B" onRemove={() => setRightId("")} />
        </div>
      ) : leftTrace ? (
        <div className="flex gap-4">
          <TracePanel trace={leftTrace} label="Trace A" onRemove={() => setLeftId("")} />
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#aeaeb2", fontSize: 13, minHeight: 300 }}>
            Select a trace for side B to compare
          </div>
        </div>
      ) : rightTrace ? (
        <div className="flex gap-4">
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#aeaeb2", fontSize: 13, minHeight: 300 }}>
            Select a trace for side A to compare
          </div>
          <TracePanel trace={rightTrace} label="Trace B" onRemove={() => setRightId("")} />
        </div>
      ) : (
        <div className="section-card">
          <div className="section-card-body" style={{ textAlign: "center", padding: 48, color: "#aeaeb2" }}>
            Select two traces above to compare their prompts, responses, and metrics
          </div>
        </div>
      )}
    </div>
  );
}
