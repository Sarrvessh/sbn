import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchPolicies, createPolicy, updatePolicy, deletePolicy, evaluatePolicies, fetchPolicyExceptions, createPolicyException, deletePolicyException } from "../lib/api";
import { formatTime } from "../lib/utils";
import { Check, X, Edit3, Trash2, Plus, ShieldAlert } from "lucide-react";
import type { Policy } from "../lib/api";

export default function Governance() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [testPolicyId, setTestPolicyId] = useState("");
  const [testInput, setTestInput] = useState("");
  const [testResult, setTestResult] = useState<{ decision: string; matched_policies: { policy_name: string }[] } | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editData, setEditData] = useState<Record<string, string>>({});
  const [showExceptions, setShowExceptions] = useState<Set<number>>(new Set());

  const { data: policies, isLoading } = useQuery({ queryKey: ["policies"], queryFn: fetchPolicies });

  const [policyError, setPolicyError] = useState<string | null>(null);
  const createMut = useMutation({
    mutationFn: (d: Record<string, unknown>) => createPolicy(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["policies"] }); setShowForm(false); },
    onError: (err) => { setPolicyError(String(err)); setTimeout(() => setPolicyError(null), 3000); },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => deletePolicy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policies"] }),
    onError: (err) => { setPolicyError(String(err)); setTimeout(() => setPolicyError(null), 3000); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) => updatePolicy(id, payload),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["policies"] }); setEditingId(null); },
    onError: (err) => { setPolicyError(String(err)); setTimeout(() => setPolicyError(null), 3000); },
  });

  const startEdit = (p: Policy) => {
    setEditingId(p.id);
    setEditData({
      name: p.name,
      description: p.description || "",
      rule_config: (p.rule_config?.pattern as string) || JSON.stringify(p.rule_config),
      action: p.action,
      severity: p.severity,
      enabled: String(p.enabled),
    });
  };

  const saveEdit = (id: number) => {
    const payload: Record<string, unknown> = {};
    if (editData.name) payload.name = editData.name;
    payload.description = editData.description || null;
    payload.rule_config = { pattern: editData.rule_config };
    payload.action = editData.action;
    payload.severity = editData.severity;
    payload.enabled = editData.enabled === "true";
    updateMut.mutate({ id, payload });
  };

  const handleTest = async () => {
    if (!testPolicyId || !testInput) return;
    try {
      setTestResult(await evaluatePolicies(testPolicyId, testInput));
    } catch (err) { setTestResult({ decision: "error", matched_policies: [{ policy_name: String(err) }] }); }
  };

  if (isLoading) return <div className="page"><div style={{ fontSize: 13, color: "#6e6e73" }}>Loading…</div></div>;

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Governance</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary btn-sm">+ Add Policy</button>
      </div>
      <p className="page-subtitle">Manage policies, compliance rules, and exceptions</p>

      {policyError && <div className="alert-banner error" style={{ marginBottom: 12 }}>{policyError}</div>}

      {showForm && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header"><div className="section-card-title">New Policy</div></div>
          <div className="section-card-body">
            <form onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              createMut.mutate({
                name: (fd.get("name") as string) || "",
                description: (fd.get("description") as string) || "",
                policy_type: (fd.get("policy_type") as string) || "",
                rule_config: { pattern: (fd.get("rule_config") as string) || "" },
                action: (fd.get("action") as string) || "flag",
                severity: (fd.get("severity") as string) || "medium",
                enabled: fd.get("enabled") === "true",
              });
            }} className="flex flex-col gap-3">
              <div className="flex gap-3">
                <input name="name" placeholder="Policy name" className="input" style={{ flex: 1 }} required />
                <input name="description" placeholder="Description" className="input" style={{ flex: 1 }} />
              </div>
              <div className="flex gap-3">
                <select name="policy_type" className="input" style={{ flex: 1 }} required>
                  <option value="keyword">keyword</option>
                  <option value="regex">regex</option>
                  <option value="llm_judge">llm_judge</option>
                  <option value="pattern">pattern</option>
                </select>
                <input name="rule_config" placeholder="Rule value" className="input" style={{ flex: 2 }} required />
                <select name="action" className="input" style={{ flex: 1 }} required>
                  <option value="flag">flag</option>
                  <option value="block">block</option>
                  <option value="require_approval">require_approval</option>
                </select>
              </div>
              <div className="flex gap-3">
                <select name="severity" className="input" style={{ flex: 1 }} defaultValue="medium">
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
                <select name="enabled" className="input" style={{ flex: 1 }} defaultValue="true">
                  <option value="true">enabled</option>
                  <option value="false">disabled</option>
                </select>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="btn btn-primary btn-sm" disabled={createMut.isPending}>{createMut.isPending ? "Creating…" : "Create Policy"}</button>
                <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary btn-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="section-card" style={{ overflow: "auto" }}>
        <table className="apple-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Action</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Config</th>
              <th>Status</th>
              <th>Updated</th>
              <th style={{ textAlign: "center" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {(!policies || policies.length === 0) ? (
              <tr><td colSpan={8} style={{ textAlign: "center", color: "#aeaeb2", padding: 24 }}>No policies defined.</td></tr>
            ) : (
              policies.map((p: Policy) => {
                const isEditing = editingId === p.id;
                const excOpen = showExceptions.has(p.id);
                return (
                  <>
                    <tr key={p.id}>
                      <td>
                        {isEditing ? (
                          <input value={editData.name} onChange={(e) => setEditData({ ...editData, name: e.target.value })} className="input" style={{ fontSize: 12, padding: "2px 6px", width: 140 }} />
                        ) : (
                          <span style={{ fontWeight: 500 }}>{p.name}</span>
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <select value={editData.action} onChange={(e) => setEditData({ ...editData, action: e.target.value })} className="input" style={{ fontSize: 11, padding: "2px 6px", width: "auto" }}>
                            <option value="flag">flag</option>
                            <option value="block">block</option>
                            <option value="require_approval">require_approval</option>
                          </select>
                        ) : (
                          <span className={`badge ${p.action === "block" ? "red" : p.action === "flag" ? "orange" : "blue"}`} style={{ fontSize: 10 }}>{p.action}</span>
                        )}
                      </td>
                      <td style={{ color: "#6e6e73", fontSize: 12 }}>{p.policy_type}</td>
                      <td>
                        {isEditing ? (
                          <select value={editData.severity} onChange={(e) => setEditData({ ...editData, severity: e.target.value })} className="input" style={{ fontSize: 11, padding: "2px 6px", width: "auto" }}>
                            <option value="low">low</option>
                            <option value="medium">medium</option>
                            <option value="high">high</option>
                          </select>
                        ) : (
                          <span className="badge" style={{ background: p.severity === "high" ? "#ffeeee" : p.severity === "medium" ? "#fff4e5" : "#e8f4fd", color: p.severity === "high" ? "#ff3b30" : p.severity === "medium" ? "#ff9500" : "#0071e3" }}>{p.severity}</span>
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input value={editData.rule_config} onChange={(e) => setEditData({ ...editData, rule_config: e.target.value })} className="input" style={{ fontSize: 11, padding: "2px 6px", width: 160, fontFamily: "'JetBrains Mono', monospace" }} />
                        ) : (
                          <span className="truncate" style={{ color: "#aeaeb2", maxWidth: 120, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, display: "inline-block" }}>
                            {(p.rule_config?.pattern as string) || JSON.stringify(p.rule_config)}
                          </span>
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <select value={editData.enabled} onChange={(e) => setEditData({ ...editData, enabled: e.target.value })} className="input" style={{ fontSize: 11, padding: "2px 6px", width: "auto" }}>
                            <option value="true">enabled</option>
                            <option value="false">disabled</option>
                          </select>
                        ) : (
                          <span className={`status-label ${p.enabled ? "green" : "gray"}`} style={{ fontSize: 11 }}>
                            <span className={`status-dot ${p.enabled ? "green" : "gray"}`} />{p.enabled ? "enabled" : "disabled"}
                          </span>
                        )}
                      </td>
                      <td style={{ color: "#aeaeb2", fontSize: 11 }}>{formatTime(p.updated_at)}</td>
                      <td style={{ textAlign: "center" }}>
                        <div className="flex items-center gap-1" style={{ justifyContent: "center" }}>
                          {isEditing ? (
                            <>
                              <button onClick={() => saveEdit(p.id)} className="btn btn-primary btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><Check size={12} /></button>
                              <button onClick={() => setEditingId(null)} className="btn btn-secondary btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><X size={12} /></button>
                            </>
                          ) : (
                            <>
                              <button onClick={() => startEdit(p)} className="btn btn-secondary btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><Edit3 size={12} /></button>
                              <button onClick={() => deleteMut.mutate(p.id)} className="btn btn-danger btn-sm" style={{ padding: "2px 6px", fontSize: 10 }}><Trash2 size={12} /></button>
                            </>
                          )}
                          <button
                            onClick={() => setShowExceptions(prev => { const n = new Set(prev); if (n.has(p.id)) n.delete(p.id); else n.add(p.id); return n; })}
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "2px 6px", fontSize: 10 }}
                          >
                            <ShieldAlert size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {excOpen && (
                      <tr key={`exc-${p.id}`}>
                        <td colSpan={8} style={{ padding: "8px 16px", background: "#fafafa" }}>
                          <ExceptionsPanel policyId={p.id} />
                        </td>
                      </tr>
                    )}
                  </>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="section-card">
        <div className="section-card-header"><div className="section-card-title">Test Policy</div></div>
        <div className="section-card-body">
          <div className="flex gap-3" style={{ marginBottom: 8 }}>
            <select value={testPolicyId} onChange={(e) => setTestPolicyId(e.target.value)} className="input" style={{ flex: 1 }}>
              <option value="">Select policy</option>
              {(policies || []).map((p: Policy) => (<option key={p.id} value={p.id}>{p.name}</option>))}
            </select>
            <input type="text" placeholder="Input to test…" value={testInput} onChange={(e) => setTestInput(e.target.value)} className="input" style={{ flex: 2 }} />
            <button onClick={handleTest} className="btn btn-primary btn-sm">Test</button>
          </div>
          {testResult && (
            <div style={{ fontSize: 12, color: testResult.decision === "block" ? "#ff3b30" : testResult.decision === "flag" ? "#ff9500" : "#34c759" }}>
              Decision: {testResult.decision}
              {testResult.matched_policies.length > 0 && <div style={{ color: "#6e6e73", marginTop: 4 }}>Matched: {testResult.matched_policies.map((p) => p.policy_name).join(", ")}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ExceptionsPanel({ policyId }: { policyId: number }) {
  const queryClient = useQueryClient();
  const [newPattern, setNewPattern] = useState("");
  const [newReason, setNewReason] = useState("");

  const { data: exceptions } = useQuery({
    queryKey: ["policy-exceptions", policyId],
    queryFn: () => fetchPolicyExceptions(policyId),
  });

  const createMut = useMutation({
    mutationFn: () => createPolicyException(policyId, newPattern.trim(), newReason.trim() || undefined),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["policy-exceptions", policyId] }); setNewPattern(""); setNewReason(""); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deletePolicyException(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policy-exceptions", policyId] }),
  });

  return (
    <div>
      <div style={{ fontSize: 11, color: "#6e6e73", marginBottom: 6, fontWeight: 600 }}>Exceptions (allowlisted patterns)</div>
      {(!exceptions || exceptions.length === 0) && <div style={{ fontSize: 11, color: "#aeaeb2", marginBottom: 6 }}>No exceptions defined.</div>}
      {exceptions?.map((exc) => (
        <div key={exc.id} className="flex items-center justify-between" style={{ padding: "4px 0", borderBottom: "1px solid #f0f0f0" }}>
          <div className="flex items-center gap-2">
            <code style={{ fontSize: 11, color: "#6e6e73" }}>{exc.pattern}</code>
            {exc.reason && <span style={{ fontSize: 10, color: "#aeaeb2" }}>— {exc.reason}</span>}
          </div>
          <button onClick={() => deleteMut.mutate(exc.id)} className="btn btn-danger btn-sm" style={{ padding: "1px 6px", fontSize: 10 }}><Trash2 size={10} /></button>
        </div>
      ))}
      <div className="flex gap-2" style={{ marginTop: 6 }}>
        <input value={newPattern} onChange={(e) => setNewPattern(e.target.value)} placeholder="Pattern to allowlist…" className="input" style={{ fontSize: 11, padding: "3px 8px", flex: 1 }} />
        <input value={newReason} onChange={(e) => setNewReason(e.target.value)} placeholder="Reason (optional)" className="input" style={{ fontSize: 11, padding: "3px 8px", flex: 1 }} />
        <button onClick={() => createMut.mutate()} disabled={!newPattern.trim() || createMut.isPending} className="btn btn-primary btn-sm" style={{ fontSize: 10, padding: "3px 8px" }}>
          <Plus size={11} /> Add
        </button>
      </div>
    </div>
  );
}
