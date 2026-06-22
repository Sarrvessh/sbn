import { useQuery } from "@tanstack/react-query";
import { fetchCostAnalytics, fetchProjects, fetchAuditLogs, fetchCostPrediction } from "../lib/api";
import { formatCost } from "../lib/utils";
import { useState } from "react";
import MetricCard from "../components/MetricCard";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, ComposedChart, Line, Legend } from "recharts";

const COLORS = ["#0071e3", "#34c759", "#ff9500", "#ff3b30", "#5e5ce6", "#64d2ff", "#ff2d55", "#30d158"];

export default function Costs() {
  const [projectFilter, setProjectFilter] = useState("");
  const projectParam = projectFilter || undefined;

  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });
  const { data: costs } = useQuery({
    queryKey: ["costs", projectParam],
    queryFn: () => fetchCostAnalytics(projectParam),
    refetchInterval: 15_000,
  });
  const { data: costPrediction } = useQuery({
    queryKey: ["cost-prediction", projectParam],
    queryFn: () => fetchCostPrediction(projectParam),
  });

  const { data: audits } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => fetchAuditLogs(50),
  });

  const teamsOverBudget = (costs?.teams || []).filter(
    (t: { name: string; budget: number; total_cost: number }) => t.budget > 0 && (t.total_cost / t.budget) * 100 >= 80
  );

  const dailyData = (costs?.daily_costs || []).map((d: { date: string; cost: number; trace_count: number }) => ({
    date: d.date.slice(5),
    cost: Number(d.cost.toFixed(4)),
    traces: d.trace_count,
  }));

  const modelData = (costs?.by_model || []).map((m: { model_name: string; total_cost: number; total_tokens: number; trace_count: number }) => ({
    name: m.model_name,
    value: m.total_cost,
    tokens: m.total_tokens,
    traces: m.trace_count,
  }));

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Cost Analytics</h1>
        <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)} className="input" style={{ width: "auto", minWidth: 130, fontSize: 12 }}>
          <option value="">All Projects</option>
          {projects?.map((p) => (<option key={p.name} value={p.name}>{p.name}</option>))}
        </select>
      </div>
      <p className="page-subtitle">Track spending and budgets across projects</p>

      {teamsOverBudget.length > 0 && (
        <div className="alert-banner warning">
          <strong>Budget Alert:</strong> {teamsOverBudget.length} team{teamsOverBudget.length > 1 ? "s" : ""} exceed 80% threshold
          <ul style={{ margin: "4px 0 0", paddingLeft: 20, fontSize: 12 }}>
            {teamsOverBudget.map((t: { name: string; budget: number; total_cost: number }) => (
              <li key={t.name}>{t.name} — {formatCost(t.total_cost)} / {formatCost(t.budget)} ({((t.total_cost / t.budget) * 100).toFixed(1)}%)</li>
            ))}
          </ul>
        </div>
      )}

      <div className="metrics">
        <MetricCard label="Total Cost" value={costs ? formatCost(costs.total_cost) : "—"} subtitle={projectFilter || "All projects"} />
        <MetricCard label="Total Tokens" value={String(costs?.total_tokens ?? "—")} />
        <MetricCard label="Avg Cost / Trace" value={costs ? formatCost(costs.total_cost / (costs.total_traces || 1)) : "—"} subtitle={`${costs?.total_traces ?? 0} traces`} />
        <MetricCard label="Cost (Month)" value={costs ? formatCost(costs.cost_this_month) : "—"} subtitle="This month" />
      </div>

      {dailyData.length > 0 && (
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">Daily Cost Trend</div>
          </div>
          <div className="section-card-body">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={dailyData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6e6e73" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#6e6e73" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v.toFixed(2)}`} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e5ea", boxShadow: "0 2px 10px rgba(0,0,0,0.08)" }}
                  formatter={(value: number, name: string) => [formatCost(value), name === "cost" ? "Cost" : "Traces"]}
                />
                <Bar dataKey="cost" fill="#0071e3" radius={[4, 4, 0, 0]} maxBarSize={32} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {modelData.length > 0 && (
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">Cost by Model</div>
          </div>
          <div className="section-card-body" style={{ display: "flex", gap: 24, alignItems: "center" }}>
            <ResponsiveContainer width="45%" height={200}>
              <PieChart>
                <Pie data={modelData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={2}>
                  {modelData.map((_: unknown, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e5ea", boxShadow: "0 2px 10px rgba(0,0,0,0.08)" }}
                  formatter={(value: number) => [formatCost(value), "Cost"]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1 }}>
              {modelData.map((m: { name: string; value: number; tokens: number; traces: number }, i: number) => (
                <div key={m.name} className="flex items-center justify-between" style={{ padding: "4px 0", borderBottom: "1px solid #f5f5f7" }}>
                  <div className="flex items-center gap-2">
                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS[i % COLORS.length], display: "inline-block" }} />
                    <span style={{ fontSize: 12 }}>{m.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6e6e73" }}>{formatCost(m.value)}</span>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#aeaeb2" }}>{m.traces} traces</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {costPrediction && (
        <div className="section-card">
          <div className="section-card-header">
            <div className="section-card-title">Cost Forecast</div>
            <span className="badge" style={{
              background: costPrediction.confidence === "high" ? "#e8f4fd" : costPrediction.confidence === "medium" ? "#fff4e5" : "#ffeeee",
              color: costPrediction.confidence === "high" ? "#0071e3" : costPrediction.confidence === "medium" ? "#ff9500" : "#ff3b30",
              fontSize: 10,
            }}>
              {costPrediction.confidence} confidence
            </span>
          </div>
          <div className="section-card-body">
            <div className="metrics" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 16 }}>
              <MetricCard label="Projected Monthly" value={formatCost(costPrediction.projected_monthly_cost)} subtitle="Based on recent avg" />
              <MetricCard label="Projected Daily Avg" value={formatCost(costPrediction.projected_daily_avg)} subtitle="Per day" />
              <MetricCard label="Confidence" value={costPrediction.confidence} subtitle={costPrediction.confidence === "high" ? "14+ days of data" : costPrediction.confidence === "medium" ? "7+ days" : "< 7 days"} />
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={costPrediction.daily_predictions} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#6e6e73" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#6e6e73" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v.toFixed(3)}`} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e5ea", boxShadow: "0 2px 10px rgba(0,0,0,0.08)" }}
                  formatter={(value: number) => [formatCost(value)]}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="actual_cost" name="Actual" fill="#0071e3" radius={[4, 4, 0, 0]} maxBarSize={24} />
                <Line dataKey="predicted_cost" name="Predicted" stroke="#ff9500" strokeWidth={2} strokeDasharray="4 3" dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="section-card" style={{ overflow: "auto" }}>
        <div className="section-card-header">
          <div className="section-card-title">Cost by Project</div>
        </div>
        <div className="section-card-body" style={{ paddingTop: 0 }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Project</th>
                <th style={{ textAlign: "right" }}>Total Cost</th>
                <th style={{ textAlign: "right" }}>Tokens</th>
                <th style={{ textAlign: "right" }}>Traces</th>
              </tr>
            </thead>
            <tbody>
              {(costs?.by_project || []).map((p: { project_name: string; total_cost: number; total_tokens: number; trace_count: number }) => (
                <tr key={p.project_name}>
                  <td style={{ fontWeight: 500 }}>{p.project_name}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{formatCost(p.total_cost)}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{p.total_tokens}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{p.trace_count}</td>
                </tr>
              ))}
              {(!costs?.by_project || costs.by_project.length === 0) && <tr><td colSpan={4} style={{ textAlign: "center", color: "#aeaeb2", padding: 24 }}>No project cost data.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-card" style={{ overflow: "auto" }}>
        <div className="section-card-header">
          <div className="section-card-title">Teams</div>
        </div>
        <div className="section-card-body" style={{ paddingTop: 0 }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Team</th>
                <th style={{ textAlign: "right" }}>Total Cost</th>
                <th style={{ textAlign: "right" }}>Budget</th>
                <th style={{ textAlign: "right" }}>Usage</th>
                <th style={{ textAlign: "right" }}>Traces</th>
                <th style={{ textAlign: "right" }}>Tokens</th>
              </tr>
            </thead>
            <tbody>
              {(costs?.teams || []).map((t: { name: string; total_cost: number; total_tokens: number; budget: number; trace_count: number }) => (
                <tr key={t.name}>
                  <td style={{ fontWeight: 500 }}>{t.name}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{formatCost(t.total_cost)}</td>
                  <td style={{ textAlign: "right", color: "#aeaeb2" }}>{t.budget > 0 ? formatCost(t.budget) : "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    {t.budget > 0 ? (
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: (t.total_cost / t.budget) >= 0.8 ? "#ff3b30" : "#34c759" }}>
                        {((t.total_cost / t.budget) * 100).toFixed(1)}%
                      </span>
                    ) : <span style={{ color: "#aeaeb2" }}>—</span>}
                  </td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{t.trace_count}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{t.total_tokens}</td>
                </tr>
              ))}
              {(!costs?.teams || costs.teams.length === 0) && <tr><td colSpan={6} style={{ textAlign: "center", color: "#aeaeb2", padding: 24 }}>No team data.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-card" style={{ overflow: "auto" }}>
        <div className="section-card-header">
          <div className="section-card-title">Cost Audit Trail</div>
        </div>
        <div className="section-card-body" style={{ paddingTop: 0 }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {(audits || []).slice(0, 30).map((a: { id: number; created_at: string; action: string; details: Record<string, unknown> | null }) => (
                <tr key={a.id}>
                  <td style={{ color: "#aeaeb2", fontSize: 12 }}>{a.created_at ? new Date(a.created_at).toLocaleString() : "—"}</td>
                  <td><span className="badge blue">{a.action}</span></td>
                  <td className="truncate" style={{ color: "#6e6e73", maxWidth: 300 }}>{a.details ? JSON.stringify(a.details) : "—"}</td>
                </tr>
              ))}
              {(!audits || audits.length === 0) && <tr><td colSpan={3} style={{ textAlign: "center", color: "#aeaeb2", padding: 24 }}>No audit logs yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
