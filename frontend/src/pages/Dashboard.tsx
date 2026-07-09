import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchMetrics, fetchGovernanceMetrics, fetchSystemMetrics, fetchRecentTraces, fetchAlerts, fetchProjects, runAgent } from "../lib/api";
import { useRealtimeEvents } from "../hooks/useWebSocket";
import { formatCost, formatLatency, formatShortTime } from "../lib/utils";
import MetricCard from "../components/MetricCard";
import { Play, ChevronRight } from "lucide-react";

export default function Dashboard() {
  const navigate = useNavigate();
  const [projectFilter, setProjectFilter] = useState("");
  const projectParam = projectFilter || undefined;

  const { data: sysMetrics } = useQuery({
    queryKey: ["system-metrics"],
    queryFn: fetchSystemMetrics,
    refetchInterval: 30_000,
  });

  const { data: governance } = useQuery({
    queryKey: ["governance-metrics", projectParam],
    queryFn: () => fetchGovernanceMetrics(projectParam),
    refetchInterval: 15_000,
  });

  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });
  const { data: metrics, refetch: refetchMetrics } = useQuery({
    queryKey: ["metrics", projectParam],
    queryFn: () => fetchMetrics(projectParam),
    refetchInterval: 10_000,
  });
  const { data: traces } = useQuery({
    queryKey: ["dashboard-traces", projectParam],
    queryFn: () => fetchRecentTraces(20, projectParam),
    refetchInterval: 10_000,
  });
  const { data: alerts } = useQuery({
    queryKey: ["dashboard-alerts", projectParam],
    queryFn: () => fetchAlerts(10, projectParam),
    refetchInterval: 10_000,
  });

  const refetchRef = useRef(refetchMetrics);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const handleMetrics = useCallback((_m: unknown) => {
    if (_m) {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => refetchRef.current(), 300);
    }
  }, []);
  useRealtimeEvents({ projectName: projectParam, onMetrics: handleMetrics });
  useEffect(() => { refetchRef.current = refetchMetrics; }, [refetchMetrics]);

  const [showRun, setShowRun] = useState(false);
  const [runResult, setRunResult] = useState<{ response: string; latency_ms: number; total_tokens: number; cost: number; flagged_for_governance: boolean } | null>(null);
  const [runError, setRunError] = useState("");
  const [runLoading, setRunLoading] = useState(false);

  const handleRun = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setRunError(""); setRunResult(null); setRunLoading(true);
    const fd = new FormData(e.currentTarget);
    try {
      const r = await runAgent({
        project_name: (fd.get("project_name") as string) || "default",
        prompt: fd.get("prompt") as string,
        model_name: (fd.get("model_name") as string) || "gpt-4o-mini",
        max_tokens: Number(fd.get("max_tokens")) || 512,
        temperature: Number(fd.get("temperature")) || 0.2,
      });
      setRunResult(r);
      refetchMetrics();
    } catch (err) { setRunError(String(err)); }
    finally { setRunLoading(false); }
  };

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 24 }}>
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>Real-time observability across your AI agents</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)} className="input" style={{ width: "auto", minWidth: 130, fontSize: 12 }}>
            <option value="">All Projects</option>
            {projects?.map((p) => (<option key={p.name} value={p.name}>{p.name}</option>))}
          </select>
          <button onClick={() => setShowRun(!showRun)} className="btn btn-primary btn-sm">
            <Play size={13} /> Run Agent
          </button>
        </div>
      </div>

      {sysMetrics && (
        <div className="section-card" style={{ marginBottom: 24 }}>
          <div className="section-card-header">
            <div className="section-card-title">System Health</div>
          </div>
          <div className="section-card-body">
            <div className="metrics" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
              <MetricCard label="Uptime" value={`${sysMetrics.uptime_hours.toFixed(1)}h`} subtitle="Server running" />
              <MetricCard label="Traces Today" value={String(sysMetrics.traces_today)} subtitle="Last 24 hours" />
              <MetricCard label="Error Rate" value={`${sysMetrics.error_rate.toFixed(2)}%`} subtitle="Last 200 traces" red={sysMetrics.error_rate > 5} />
              <MetricCard label="Active Projects" value={String(sysMetrics.total_projects)} subtitle={`${sysMetrics.unique_models.length} models`} />
            </div>
          </div>
        </div>
      )}

      {governance && (
        <div className="section-card" style={{ marginBottom: 24 }}>
          <div className="section-card-header">
            <div className="section-card-title">Governance &amp; Safety</div>
            <span onClick={() => navigate("/oversight")} className="link" style={{ cursor: "pointer", fontSize: 12 }}>
              View Oversight <ChevronRight size={12} style={{ verticalAlign: "middle" }} />
            </span>
          </div>
          <div className="section-card-body">
            <div className="metrics" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 12 }}>
              <MetricCard label="Flagged Traces" value={`${governance.flag_rate}%`} subtitle={`${governance.total_flagged} of ${governance.total_traces} traces`} accent />
              <MetricCard label="Pending Reviews" value={String(governance.pending_reviews)} subtitle={governance.pending_reviews > 0 ? "Awaiting review" : "All caught up"} />
              <MetricCard label="Approved" value={String(governance.approved_reviews)} subtitle="Approved reviews" green />
              <MetricCard label="Rejected" value={String(governance.rejected_reviews)} subtitle="Rejected reviews" red />
            </div>
            {governance.by_severity.length > 0 && (
              <div className="flex items-center gap-4" style={{ fontSize: 12, color: "#6e6e73" }}>
                <span style={{ fontWeight: 500, color: "#1d1d1f" }}>Policies by severity:</span>
                {governance.by_severity.map((s: { severity: string; count: number }) => (
                  <span key={s.severity} className="badge" style={{
                    background: s.severity === "high" ? "#ffeeee" : s.severity === "medium" ? "#fff4e5" : "#e8f4fd",
                    color: s.severity === "high" ? "#ff3b30" : s.severity === "medium" ? "#ff9500" : "#0071e3",
                  }}>
                    {s.severity}: {s.count}
                  </span>
                ))}
              </div>
            )}
            {governance.recent_flags.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 11, color: "#aeaeb2", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Recent Flags</div>
                <div className="flex flex-col gap-1">
                  {governance.recent_flags.map((f: { request_id: string; project_name: string; status: string }) => (
                    <div key={f.request_id} className="flex items-center gap-2" style={{ fontSize: 12 }}>
                      <span className={`status-dot ${f.status === "error" ? "red" : "orange"}`} />
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{f.request_id.slice(0, 16)}...</span>
                      <span style={{ color: "#6e6e73" }}>{f.project_name}</span>
                      <span className="badge" style={{ fontSize: 10 }}>{f.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {showRun && (
        <div className="section-card" style={{ marginBottom: 24 }}>
          <div className="section-card-header">
            <div className="section-card-title">Run Live Agent</div>
          </div>
          <div className="section-card-body">
            <form onSubmit={handleRun} className="flex flex-col gap-3">
              <div className="flex gap-3">
                <input name="project_name" placeholder="Project" defaultValue={projectFilter || "default"} key={projectFilter || "default"} className="input" style={{ flex: 1 }} />
                <input name="model_name" placeholder="Model" defaultValue="gpt-4o-mini" className="input" style={{ flex: 1 }} />
                <input name="max_tokens" type="number" placeholder="Max tokens" defaultValue={512} className="input" style={{ flex: 0.5 }} />
                <input name="temperature" type="number" step="0.1" placeholder="Temp" defaultValue={0.2} className="input" style={{ flex: 0.5 }} />
              </div>
              <textarea name="prompt" placeholder="Enter a prompt..." rows={2} className="input" required />
              <div className="flex gap-2">
                <button type="submit" disabled={runLoading} className="btn btn-primary">{runLoading ? "Running…" : "Execute"}</button>
                <button type="button" onClick={() => setShowRun(false)} className="btn btn-secondary">Cancel</button>
              </div>
            </form>
            {runError && <div className="alert-banner error mt-2">{runError}</div>}
            {runResult && (
              <div className="mt-3">
                <pre className="code-block" style={{ maxHeight: 150, overflow: "auto" }}>{runResult.response || ""}</pre>
                <div className="flex gap-4 mt-1" style={{ fontSize: 12, color: "#6e6e73" }}>
                  <span>{formatLatency(runResult.latency_ms)}</span>
                  <span>{(runResult.total_tokens ?? 0)} tokens</span>
                  <span>{formatCost(runResult.cost)}</span>
                  <span style={{ color: runResult.flagged_for_governance ? "#ff3b30" : "#34c759" }}>
                    {runResult.flagged_for_governance ? "Flagged" : "Clean"}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="metrics">
        <MetricCard label="Total Cost" value={metrics ? formatCost(metrics.total_cost) : "—"} subtitle="All time spend" />
        <MetricCard label="Avg Latency (50)" value={metrics ? formatLatency(metrics.average_latency_last_50_ms) : "—"} subtitle="Last 50 traces" />
        <MetricCard label="P95 Latency (50)" value={metrics ? formatLatency(metrics.p95_latency_last_50_ms) : "—"} subtitle="Last 50 traces" />
        <MetricCard label="Error Rate (50)" value={metrics && metrics.error_rate_last_50_percent != null ? `${metrics.error_rate_last_50_percent.toFixed(2)}%` : "—"} subtitle="Last 50 traces" red={metrics ? (metrics.error_rate_last_50_percent || 0) > 5 : false} />
        <MetricCard label="Governance Flags" value={metrics ? String(metrics.governance_flagged_count) : "—"} subtitle="Active flags" accent />
        <MetricCard label="Traces (24h)" value={metrics ? String(metrics.traces_last_24h) : "—"} subtitle="Last 24 hours" />
      </div>

      <div className="section-card">
        <div className="section-card-header">
          <div className="section-card-title">Recent Traces</div>
          <span onClick={() => navigate("/traces")} className="link" style={{ cursor: "pointer", fontSize: 12 }}>
            View All <ChevronRight size={12} style={{ verticalAlign: "middle" }} />
          </span>
        </div>
        <div className="section-card-body" style={{ paddingTop: 0 }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Project</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Latency</th>
                <th style={{ textAlign: "right" }}>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {traces?.slice(0, 8).map((t) => (
                <tr key={t.request_id} onClick={() => navigate(`/traces/${t.request_id}`)}>
                  <td style={{ color: "#aeaeb2", fontSize: 12 }}>{formatShortTime(t.timestamp)}</td>
                  <td style={{ fontWeight: 500 }}>{t.project_name}</td>
                  <td><span className={`status-label ${t.status === "success" ? "green" : "red"}`} style={{ fontSize: 12 }}><span className={`status-dot ${t.status === "success" ? "green" : "red"}`} />{t.status}</span></td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{formatLatency(t.latency_ms)}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{t.total_tokens}</td>
                </tr>
              ))}
              {(!traces || traces.length === 0) && <tr><td colSpan={5} style={{ textAlign: "center", color: "#aeaeb2", padding: 24, fontSize: 13 }}>No traces yet</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-card">
        <div className="section-card-header">
          <div className="section-card-title">Recent Alerts</div>
          <span onClick={() => navigate("/alerts")} className="link" style={{ cursor: "pointer", fontSize: 12 }}>
            View All <ChevronRight size={12} style={{ verticalAlign: "middle" }} />
          </span>
        </div>
        <div className="section-card-body" style={{ paddingTop: 0 }}>
          <ul className="item-list">
            {alerts?.slice(0, 5).map((a) => (
              <li key={`${a.request_id}-${a.alert_type}`}>
                <div className="flex items-center gap-2">
                  <span className={`status-dot ${a.severity === "high" ? "red" : a.severity === "medium" ? "orange" : "blue"}`} />
                  <span className="badge" style={{ background: a.severity === "high" ? "#ffeeee" : a.severity === "medium" ? "#fff4e5" : "#e8f4fd", color: a.severity === "high" ? "#ff3b30" : a.severity === "medium" ? "#ff9500" : "#0071e3" }}>
                    {a.severity}
                  </span>
                  <span style={{ color: "#1d1d1f", fontWeight: 500 }}>{a.alert_type}</span>
                  <span className="truncate" style={{ color: "#6e6e73", maxWidth: 300 }}>{a.message}</span>
                </div>
              </li>
            ))}
            {(!alerts || alerts.length === 0) && <li style={{ cursor: "default", color: "#aeaeb2" }}>No alerts</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
