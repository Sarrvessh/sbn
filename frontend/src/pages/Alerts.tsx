import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchAlertRules, fetchAlerts, fetchProjects, createAlertRule, updateAlertRule, deleteAlertRule, type AlertRule } from "../lib/api";
import { formatTime } from "../lib/utils";
import { useState } from "react";

type Tab = "feed" | "rules";

const ALERT_TYPES = ["high_latency", "high_cost", "error_rate", "governance"];
const SEVERITIES = ["low", "medium", "high"];

function emptyForm(): Partial<AlertRule> {
  return { name: "", project_name: null, alert_type: "high_latency", severity: "medium", threshold_value: 0, enabled: true };
}

export default function Alerts() {
  const [tab, setTab] = useState<Tab>("feed");
  const [projectFilter, setProjectFilter] = useState("");
  const projectParam = projectFilter || undefined;

  const queryClient = useQueryClient();
  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });
  const { data: alerts, isLoading } = useQuery({
    queryKey: ["alerts", projectParam],
    queryFn: () => fetchAlerts(200, projectParam),
    refetchInterval: 15_000,
  });
  const { data: rules } = useQuery({ queryKey: ["alert-rules"], queryFn: fetchAlertRules });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<Partial<AlertRule>>(emptyForm());

  const createMut = useMutation({
    mutationFn: createAlertRule,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["alert-rules"] }); setForm(emptyForm()); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) => updateAlertRule(id, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["alert-rules"] }); setEditingId(null); setForm(emptyForm()); },
  });
  const deleteMut = useMutation({
    mutationFn: deleteAlertRule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  });

  const severityOrder = ["high", "medium", "low"];
  const sorted = [...(alerts || [])].sort((a, b) => severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity));

  function startEdit(r: AlertRule) {
    setEditingId(r.id);
    setForm({ ...r });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm());
  }

  function saveRule() {
    if (editingId !== null) {
      const payload: Record<string, unknown> = {};
      if (form.name !== undefined) payload.name = form.name;
      if (form.project_name !== undefined) payload.project_name = form.project_name || null;
      if (form.alert_type !== undefined) payload.alert_type = form.alert_type;
      if (form.severity !== undefined) payload.severity = form.severity;
      if (form.threshold_value !== undefined) payload.threshold_value = form.threshold_value;
      if (form.enabled !== undefined) payload.enabled = form.enabled;
      updateMut.mutate({ id: editingId, payload });
    } else {
      createMut.mutate({
        name: form.name || "",
        alert_type: form.alert_type || "high_latency",
        severity: form.severity || "medium",
        threshold_value: form.threshold_value || 0,
        enabled: form.enabled ?? true,
        project_name: form.project_name || null,
      });
    }
  }

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Alerts</h1>
        <div className="flex items-center gap-2">
          <div className="tabs" style={{ marginRight: 8 }}>
            <button className={`tab ${tab === "feed" ? "active" : ""}`} onClick={() => setTab("feed")}>Feed</button>
            <button className={`tab ${tab === "rules" ? "active" : ""}`} onClick={() => setTab("rules")}>Rules</button>
          </div>
          {tab === "feed" && (
            <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)} className="input" style={{ width: "auto", minWidth: 130, fontSize: 12 }}>
              <option value="">All Projects</option>
              {projects?.map((p) => (<option key={p.name} value={p.name}>{p.name}</option>))}
            </select>
          )}
        </div>
      </div>
      <p className="page-subtitle">Monitor governance and system alerts</p>

      {tab === "feed" && (
        <>
          {isLoading ? (
            <div style={{ fontSize: 13, color: "#6e6e73" }}>Loading…</div>
          ) : (
            <div className="section-card">
              <ul className="item-list">
                {sorted.map((a, i) => (
                  <li key={`${a.request_id}-${a.alert_type}`} style={{ cursor: "default" }}>
                    <div className="flex items-center gap-3" style={{ flex: 1, minWidth: 0 }}>
                      <span className={`status-dot ${a.severity === "high" ? "red" : a.severity === "medium" ? "orange" : "blue"}`} />
                      <span className="badge" style={{ background: a.severity === "high" ? "#ffeeee" : a.severity === "medium" ? "#fff4e5" : "#e8f4fd", color: a.severity === "high" ? "#ff3b30" : a.severity === "medium" ? "#ff9500" : "#0071e3" }}>
                        {a.severity}
                      </span>
                      <span style={{ fontWeight: 500, color: "#1d1d1f" }}>{a.alert_type}</span>
                      <span className="truncate" style={{ color: "#6e6e73", flex: 1 }}>{a.message}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#aeaeb2" }}>{formatTime(a.timestamp)}</span>
                      {a.request_id && <span className="truncate" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#aeaeb2", maxWidth: 140 }}>{a.request_id}</span>}
                    </div>
                  </li>
                ))}
                {sorted.length === 0 && <li style={{ cursor: "default", color: "#aeaeb2" }}>No alerts to display.</li>}
              </ul>
            </div>
          )}
        </>
      )}

      {tab === "rules" && (
        <div className="section-card" style={{ padding: 16 }}>
          <div className="flex items-center gap-3" style={{ marginBottom: 16, flexWrap: "wrap" }}>
            <input className="input" placeholder="Rule name" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: 160 }} />
            <select className="input" value={form.project_name || ""} onChange={(e) => setForm({ ...form, project_name: e.target.value || null })} style={{ width: 140 }}>
              <option value="">Global</option>
              {projects?.map((p) => (<option key={p.name} value={p.name}>{p.name}</option>))}
            </select>
            <select className="input" value={form.alert_type || "high_latency"} onChange={(e) => setForm({ ...form, alert_type: e.target.value })} style={{ width: 130 }}>
              {ALERT_TYPES.map((t) => (<option key={t} value={t}>{t}</option>))}
            </select>
            <select className="input" value={form.severity || "medium"} onChange={(e) => setForm({ ...form, severity: e.target.value })} style={{ width: 100 }}>
              {SEVERITIES.map((s) => (<option key={s} value={s}>{s}</option>))}
            </select>
            <input className="input" type="number" step="any" min="0" placeholder="Threshold" value={form.threshold_value ?? ""} onChange={(e) => setForm({ ...form, threshold_value: parseFloat(e.target.value) || 0 })} style={{ width: 110 }} />
            <label className="flex items-center gap-1" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
              <input type="checkbox" checked={form.enabled ?? true} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
              Enabled
            </label>
            {editingId !== null ? (
              <>
                <button className="btn btn-primary" onClick={saveRule} style={{ fontSize: 12 }}>Update</button>
                <button className="btn" onClick={cancelEdit} style={{ fontSize: 12 }}>Cancel</button>
              </>
            ) : (
              <button className="btn btn-primary" onClick={saveRule} style={{ fontSize: 12 }}>Add Rule</button>
            )}
          </div>

          <table className="table" style={{ width: "100%", fontSize: 12 }}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Project</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Threshold</th>
                <th>Enabled</th>
                <th style={{ width: 80 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(rules || []).map((r) => (
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td>{r.project_name || <span style={{ color: "#aeaeb2" }}>Global</span>}</td>
                  <td><span className="badge">{r.alert_type}</span></td>
                  <td><span className="badge" style={{ background: r.severity === "high" ? "#ffeeee" : r.severity === "medium" ? "#fff4e5" : "#e8f4fd", color: r.severity === "high" ? "#ff3b30" : r.severity === "medium" ? "#ff9500" : "#0071e3" }}>{r.severity}</span></td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace" }}>{r.threshold_value}</td>
                  <td>{r.enabled ? "Yes" : "No"}</td>
                  <td>
                    <div className="flex items-center gap-1">
                      <button className="btn" style={{ fontSize: 11, padding: "2px 8px" }} onClick={() => startEdit(r)}>Edit</button>
                      <button className="btn" style={{ fontSize: 11, padding: "2px 8px", color: "#ff3b30" }} onClick={() => deleteMut.mutate(r.id)}>Del</button>
                    </div>
                  </td>
                </tr>
              ))}
              {(!rules || rules.length === 0) && (
                <tr><td colSpan={7} style={{ textAlign: "center", color: "#aeaeb2", padding: 16 }}>No alert rules configured.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
