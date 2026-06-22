import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchWebhooks, createWebhook, updateWebhook, deleteWebhook, fetchWebhookDeliveries, testWebhook } from "../lib/api";
import { formatTime } from "../lib/utils";
import { useState } from "react";
import { Plus, Trash2, Edit3, Send, Check, X, Eye } from "lucide-react";

const EVENT_OPTIONS = [
  "alert.execution_error",
  "alert.high_latency",
  "alert.high_cost",
  "alert.governance",
  "trace.created",
  "trace.flagged",
];

export default function Webhooks() {
  const queryClient = useQueryClient();
  const { data: webhooks } = useQuery({ queryKey: ["webhooks"], queryFn: fetchWebhooks });

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({ name: "", url: "", secret: "", events: [] as string[], enabled: true });
  const [viewDeliveries, setViewDeliveries] = useState<number | null>(null);
  const [testUrl, setTestUrl] = useState("");
  const [testSecret, setTestSecret] = useState("");
  const [testResult, setTestResult] = useState<{ success: boolean; status_code: number | null; response_body: string | null; error?: string } | null>(null);

  const createMut = useMutation({
    mutationFn: () => createWebhook({ ...formData, secret: formData.secret || undefined }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["webhooks"] }); setShowForm(false); resetForm(); },
  });
  const updateMut = useMutation({
    mutationFn: () => updateWebhook(editingId!, formData),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["webhooks"] }); setEditingId(null); resetForm(); },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteWebhook(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["webhooks"] }),
  });

  const resetForm = () => setFormData({ name: "", url: "", secret: "", events: [], enabled: true });

  const startEdit = (w: typeof formData & { id: number }) => {
    setEditingId(w.id);
    setFormData({ name: w.name, url: w.url, secret: "", events: w.events, enabled: w.enabled });
  };

  const toggleEvent = (e: string) => {
    setFormData((prev) => ({
      ...prev,
      events: prev.events.includes(e) ? prev.events.filter((x) => x !== e) : [...prev.events, e],
    }));
  };

  const handleTest = async () => {
    setTestResult(null);
    try {
      setTestResult(await testWebhook(testUrl, testSecret || undefined));
    } catch (err) { setTestResult({ success: false, status_code: null, response_body: null, error: String(err) }); }
  };

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Webhooks</h1>
        <button onClick={() => { setShowForm(!showForm); setEditingId(null); resetForm(); }} className="btn btn-primary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
          <Plus size={12} /> {showForm ? "Cancel" : "New Webhook"}
        </button>
      </div>
      <p className="page-subtitle">Configure webhook notifications for alerts and events</p>

      {showForm && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header"><div className="section-card-title">Create Webhook</div></div>
          <div className="section-card-body">
            <div className="flex flex-col gap-3">
              <div className="flex gap-3">
                <input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="Name" className="input" style={{ flex: 1 }} />
                <input value={formData.url} onChange={(e) => setFormData({ ...formData, url: e.target.value })} placeholder="https://hooks.slack.com/..." className="input" style={{ flex: 2 }} />
              </div>
              <div className="flex gap-3">
                <input value={formData.secret} onChange={(e) => setFormData({ ...formData, secret: e.target.value })} placeholder="Secret (optional)" type="password" className="input" style={{ flex: 1 }} />
                <label className="flex items-center gap-2" style={{ fontSize: 12, color: "#6e6e73", cursor: "pointer" }}>
                  <input type="checkbox" checked={formData.enabled} onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })} style={{ accentColor: "#0071e3" }} />
                  Enabled
                </label>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#6e6e73", marginBottom: 6 }}>Events</div>
                <div className="flex flex-wrap gap-2">
                  {EVENT_OPTIONS.map((ev) => (
                    <label key={ev} className="flex items-center gap-1.5" style={{ fontSize: 11, cursor: "pointer", padding: "4px 8px", borderRadius: 6, background: formData.events.includes(ev) ? "#0071e3" : "#f5f5f7", color: formData.events.includes(ev) ? "#fff" : "#6e6e73" }}>
                      <input type="checkbox" checked={formData.events.includes(ev)} onChange={() => toggleEvent(ev)} style={{ display: "none" }} />
                      {ev}
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => editingId ? updateMut.mutate() : createMut.mutate()} disabled={!formData.name || !formData.url} className="btn btn-primary btn-sm">
                  {editingId ? "Update" : "Create"}
                </button>
                <button onClick={() => { setShowForm(false); setEditingId(null); resetForm(); }} className="btn btn-secondary btn-sm">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="section-card" style={{ overflow: "auto" }}>
        <table className="apple-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>URL</th>
              <th>Events</th>
              <th>Status</th>
              <th>Updated</th>
              <th style={{ textAlign: "center" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {!webhooks || webhooks.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>No webhooks configured.</td></tr>
            ) : (
              webhooks.map((w) => (
                <tr key={w.id}>
                  <td style={{ fontWeight: 500 }}>{w.name}</td>
                  <td style={{ color: "#6e6e73", fontSize: 12, maxWidth: 250, overflow: "hidden", textOverflow: "ellipsis" }}>{w.url}</td>
                  <td style={{ fontSize: 11 }}>{(w.events || []).slice(0, 2).join(", ")}{(w.events || []).length > 2 ? ` +${w.events.length - 2}` : ""}</td>
                  <td><span className={`status-label ${w.enabled ? "green" : "gray"}`} style={{ fontSize: 11 }}><span className={`status-dot ${w.enabled ? "green" : "gray"}`} />{w.enabled ? "active" : "disabled"}</span></td>
                  <td style={{ color: "#aeaeb2", fontSize: 11 }}>{formatTime(w.updated_at)}</td>
                  <td style={{ textAlign: "center" }}>
                    <div className="flex items-center gap-1" style={{ justifyContent: "center" }}>
                      <button onClick={() => { setShowForm(true); startEdit(w); }} className="btn btn-secondary btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><Edit3 size={12} /></button>
                      <button onClick={() => setViewDeliveries(viewDeliveries === w.id ? null : w.id)} className="btn btn-secondary btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><Eye size={12} /></button>
                      <button onClick={() => deleteMut.mutate(w.id)} className="btn btn-danger btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><Trash2 size={12} /></button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {viewDeliveries !== null && <DeliveriesPanel webhookId={viewDeliveries} onClose={() => setViewDeliveries(null)} />}

      <div className="section-card">
        <div className="section-card-header"><div className="section-card-title">Test Webhook</div></div>
        <div className="section-card-body">
          <div className="flex gap-3" style={{ marginBottom: 8 }}>
            <input value={testUrl} onChange={(e) => setTestUrl(e.target.value)} placeholder="https://hooks.slack.com/..." className="input" style={{ flex: 2 }} />
            <input value={testSecret} onChange={(e) => setTestSecret(e.target.value)} placeholder="Secret (optional)" type="password" className="input" style={{ flex: 1 }} />
            <button onClick={handleTest} className="btn btn-primary btn-sm" style={{ display: "flex", alignItems: "center", gap: 4 }}><Send size={12} /> Test</button>
          </div>
          {testResult && (
            <div style={{ fontSize: 12, padding: 8, borderRadius: 6, background: testResult.success ? "#e8f4fd" : "#ffeeee", color: testResult.success ? "#0071e3" : "#ff3b30" }}>
              {testResult.success ? <><Check size={12} /> Delivered (HTTP {testResult.status_code})</> : <><X size={12} /> Failed: {testResult.error || `HTTP ${testResult.status_code}`}</>}
              {testResult.response_body && <pre className="code-block" style={{ marginTop: 4, fontSize: 11, maxHeight: 100 }}>{testResult.response_body}</pre>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DeliveriesPanel({ webhookId, onClose }: { webhookId: number; onClose: () => void }) {
  const { data: deliveries } = useQuery({
    queryKey: ["webhook-deliveries", webhookId],
    queryFn: () => fetchWebhookDeliveries(webhookId),
    refetchInterval: 5000,
  });

  return (
    <div className="section-card" style={{ marginTop: 8 }}>
      <div className="section-card-header">
        <div className="section-card-title">Delivery Log</div>
        <button onClick={onClose} className="btn btn-secondary btn-sm" style={{ fontSize: 10 }}>Close</button>
      </div>
      <div className="section-card-body" style={{ paddingTop: 0 }}>
        {!deliveries || deliveries.length === 0 ? (
          <div style={{ fontSize: 12, color: "#aeaeb2", padding: 12 }}>No deliveries yet.</div>
        ) : (
          deliveries.map((d) => (
            <div key={d.id} className="flex items-start gap-3" style={{ padding: "8px 0", borderBottom: "1px solid #f5f5f7", fontSize: 12 }}>
              <span className={`status-dot ${d.status === "success" ? "green" : "red"}`} />
              <div style={{ flex: 1 }}>
                <div className="flex items-center gap-2">
                  <span className="badge" style={{ fontSize: 10 }}>{d.event_type}</span>
                  <span style={{ color: d.status === "success" ? "#34c759" : "#ff3b30", fontWeight: 500 }}>{d.status}</span>
                  {d.status_code && <span style={{ color: "#aeaeb2" }}>HTTP {d.status_code}</span>}
                </div>
                <div style={{ color: "#aeaeb2", fontSize: 11 }}>{formatTime(d.delivered_at)}</div>
                {d.response_body && <pre className="code-block" style={{ marginTop: 4, fontSize: 10, maxHeight: 80 }}>{d.response_body}</pre>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
