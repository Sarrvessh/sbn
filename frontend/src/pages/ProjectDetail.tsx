import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchProjectDetail, fetchRecentTraces, deleteProject } from "../lib/api";
import { formatTime, formatCost, formatLatency } from "../lib/utils";
import { ArrowLeft, Trash2 } from "lucide-react";
import { useState } from "react";
import type { RecentTrace } from "../lib/api";

export default function ProjectDetail() {
  const { projectName } = useParams<{ projectName: string }>();
  const navigate = useNavigate();
  const name = projectName || "";

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", name],
    queryFn: () => fetchProjectDetail(name),
    enabled: !!name,
  });

  const { data: traces } = useQuery({
    queryKey: ["traces", name],
    queryFn: () => fetchRecentTraces(100, name),
    enabled: !!name,
  });

  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete project "${name}" and all its traces?`)) return;
    setDeleting(true);
    try {
      await deleteProject(name);
      navigate("/projects", { replace: true });
    } catch { }
    setDeleting(false);
  };

  if (isLoading) return <div className="page"><div style={{ fontSize: 13, color: "#6e6e73" }}>Loading project…</div></div>;
  if (!project) return <div className="page"><div style={{ fontSize: 13, color: "#ff3b30" }}>Project not found.</div></div>;

  return (
    <div className="page">
      <button onClick={() => navigate("/projects")} className="link" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
        <ArrowLeft size={14} /> Back to Projects
      </button>

      <div className="flex items-start justify-between" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="page-title" style={{ fontSize: 24 }}>{project.name}</h1>
          {project.description && <p style={{ fontSize: 12, color: "#6e6e73", marginTop: 2 }}>{project.description}</p>}
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="btn btn-danger btn-sm"
          style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}
        >
          <Trash2 size={12} />
          {deleting ? "..." : "Delete Project"}
        </button>
      </div>

      <div className="metrics" style={{ marginBottom: 24, gridTemplateColumns: "repeat(4, 1fr)" }}>
        <div className="metric-card">
          <div className="metric-label">Total Cost</div>
          <div className="metric-value" style={{ fontSize: 16 }}>{formatCost(project.total_cost)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Total Traces</div>
          <div className="metric-value" style={{ fontSize: 16 }}>{project.total_traces}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Success Rate</div>
          <div className="metric-value" style={{ fontSize: 16 }}>{project.success_rate}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Latency</div>
          <div className="metric-value" style={{ fontSize: 16 }}>{formatLatency(project.average_latency_ms)}</div>
        </div>
      </div>

      <div className="metrics" style={{ marginBottom: 24, gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="metric-card">
          <div className="metric-label">Total Tokens</div>
          <div className="metric-value" style={{ fontSize: 14, fontFamily: "'JetBrains Mono', monospace" }}>{project.total_tokens}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Models Used</div>
          <div className="metric-value" style={{ fontSize: 13, fontFamily: "'Inter', sans-serif" }}>{(project.models_used || []).join(", ") || "—"}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">First Trace</div>
          <div className="metric-value" style={{ fontSize: 13, fontFamily: "'Inter', sans-serif" }}>{formatTime(project.first_trace_at)}</div>
        </div>
      </div>

      <div className="section-card" style={{ overflow: "auto" }}>
        <div className="section-card-header">
          <div className="section-card-title">Traces ({project.total_traces})</div>
        </div>
        <table className="apple-table">
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Model</th>
              <th style={{ textAlign: "right" }}>Tokens</th>
              <th style={{ textAlign: "right" }}>Cost</th>
              <th style={{ textAlign: "right" }}>Latency</th>
              <th>Status</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {(traces || []).length === 0 ? (
              <tr><td colSpan={7} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>No traces yet.</td></tr>
            ) : (
              (traces || []).map((t: RecentTrace) => (
                <tr key={t.request_id} onClick={() => navigate(`/traces/${t.request_id}`)} style={{ cursor: "pointer" }}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{t.request_id}</td>
                  <td style={{ fontSize: 12, color: "#6e6e73" }}>{t.model_name}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{t.total_tokens}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{formatCost(t.cost)}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{formatLatency(t.latency_ms)}</td>
                  <td>
                    <span className={`status-label ${t.status === "success" ? "green" : "red"}`}>
                      <span className={`status-dot ${t.status === "success" ? "green" : "red"}`} />{t.status}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: "#6e6e73" }}>{formatTime(t.timestamp)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
