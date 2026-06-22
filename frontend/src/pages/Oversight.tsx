import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchReviewQueue, reviewAction, fetchReviewed, fetchPolicies, evaluatePolicies, fetchEscalationRules, createEscalationRule, deleteEscalationRule } from "../lib/api";

type Tab = "pending" | "reviewed" | "governance" | "escalation";

export default function Oversight() {
  const [tab, setTab] = useState<Tab>("pending");
  const [redact, setRedact] = useState(false);
  const tabs: { key: Tab; label: string }[] = [
    { key: "pending", label: "Pending Reviews" },
    { key: "reviewed", label: "Reviewed" },
    { key: "governance", label: "Governance Policy" },
    { key: "escalation", label: "Escalation Rules" },
  ];

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Oversight</h1>
        <label className="flex items-center gap-1.5" style={{ fontSize: 12, color: "#6e6e73", cursor: "pointer" }}>
          <input type="checkbox" checked={redact} onChange={(e) => setRedact(e.target.checked)} style={{ accentColor: "#0071e3" }} />
          Redact PII
        </label>
      </div>
      <p className="page-subtitle">Review, policy, and escalation management</p>

      <div className="segmented">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={tab === t.key ? "active" : ""}>{t.label}</button>
        ))}
      </div>

      {tab === "pending" && <PendingReviews redact={redact} />}
      {tab === "reviewed" && <ReviewedReviews redact={redact} />}
      {tab === "governance" && <GovernancePanel />}
      {tab === "escalation" && <EscalationRulesPanel />}
    </div>
  );
}

function PendingReviews({ redact }: { redact: boolean }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["reviews", "pending", redact],
    queryFn: () => fetchReviewQueue(redact),
    refetchInterval: 10_000,
  });
  const [reviewError, setReviewError] = useState<string | null>(null);
  const reviewMut = useMutation({
    mutationFn: ({ requestId, status, reason }: { requestId: string; status: string; reason?: string }) => reviewAction(requestId, status, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reviews"] }),
    onError: (err) => { setReviewError(String(err)); setTimeout(() => setReviewError(null), 3000); },
  });
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>({});

  if (isLoading) return <div style={{ fontSize: 13, color: "#6e6e73" }}>Loading…</div>;
  if (!data || data.length === 0) return <div style={{ fontSize: 13, color: "#aeaeb2" }}>No pending reviews.</div>;

  return (
    <div>
      {reviewError && <div className="alert-banner" style={{ marginBottom: 12, color: "#ff3b30", fontSize: 12 }}>{reviewError}</div>}
      {data.map((r: { request_id: string; prompt_preview: string; response_preview: string }) => (
        <div key={r.request_id} className="section-card">
          <div className="section-card-header">
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#aeaeb2" }}>{r.request_id}</span>
          </div>
          <div className="section-card-body">
            <div className="flex gap-4" style={{ marginBottom: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#aeaeb2", marginBottom: 4 }}>Prompt</div>
                <pre className="code-block" style={{ maxHeight: 80, overflow: "auto", fontSize: 11 }}>{r.prompt_preview || "(empty)"}</pre>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "#aeaeb2", marginBottom: 4 }}>Response</div>
                <pre className="code-block" style={{ maxHeight: 80, overflow: "auto", fontSize: 11 }}>{r.response_preview || "(empty)"}</pre>
              </div>
            </div>
            {rejectId === r.request_id && (
              <div style={{ marginBottom: 8 }}>
                <textarea
                  placeholder="Reason for rejection…" className="input" rows={2} style={{ marginBottom: 4 }}
                  value={rejectReasons[r.request_id] || ""}
                  onChange={(e) => setRejectReasons((prev) => ({ ...prev, [r.request_id]: e.target.value }))}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Escape") setRejectId(null);
                  }}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      reviewMut.mutate({ requestId: r.request_id, status: "rejected", reason: rejectReasons[r.request_id] || "" });
                      setRejectId(null);
                    }}
                    className="btn btn-danger btn-sm" disabled={reviewMut.isPending}
                  >Confirm Reject</button>
                  <button onClick={() => { setRejectId(null); setRejectReasons((prev) => { const n = { ...prev }; delete n[r.request_id]; return n; }); }} className="btn btn-secondary btn-sm">Cancel</button>
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={() => reviewMut.mutate({ requestId: r.request_id, status: "approved" })} className="btn btn-primary btn-sm" disabled={reviewMut.isPending}>Approve</button>
              <button onClick={() => setRejectId(r.request_id)} className="btn btn-danger btn-sm" disabled={reviewMut.isPending}>Reject</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ReviewedReviews({ redact }: { redact: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ["reviews", "reviewed", redact],
    queryFn: () => fetchReviewed(redact),
  });
  if (isLoading) return <div style={{ fontSize: 13, color: "#6e6e73" }}>Loading…</div>;
  if (!data || data.length === 0) return <div style={{ fontSize: 13, color: "#aeaeb2" }}>No reviewed items yet.</div>;
  return (
    <div className="section-card" style={{ overflow: "auto" }}>
      <table className="apple-table">
        <thead>
          <tr>
            <th>Request ID</th>
            <th>Status</th>
            <th>Reviewer</th>
            <th>Notes</th>
            <th>Prompt</th>
            <th>Response</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r: { request_id: string; prompt_preview: string; response_preview: string; latest_review: { id: number; decision: string; reviewer: string; notes?: string } | null }) => {
            const lr = r.latest_review;
            const status = lr?.decision || "pending";
            return (
              <tr key={lr?.id ?? r.request_id}>
                <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#aeaeb2" }}>{r.request_id}</td>
                <td><span className={`status-label ${status === "approved" ? "green" : "red"}`} style={{ fontSize: 12 }}><span className={`status-dot ${status === "approved" ? "green" : "red"}`} />{status}</span></td>
                <td style={{ color: "#6e6e73" }}>{lr?.reviewer || "—"}</td>
                <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 120 }}>{lr?.notes || "—"}</td>
                <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 150 }}>{r.prompt_preview}</td>
                <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 150 }}>{r.response_preview}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function GovernancePanel() {
  const [testPolicyId, setTestPolicyId] = useState("");
  const [testInput, setTestInput] = useState("");
  const [testResult, setTestResult] = useState<{ decision: string; matched_policies: { policy_name: string }[] } | null>(null);

  const { data: policies, isLoading } = useQuery({ queryKey: ["policies"], queryFn: fetchPolicies });

  const handleTest = async () => {
    if (!testPolicyId || !testInput) return;
    try {
      const res = await evaluatePolicies(testPolicyId, testInput);
      setTestResult(res);
    } catch (err) { setTestResult({ decision: "error", matched_policies: [{ policy_name: String(err) }] }); }
  };

  if (isLoading) return <div style={{ fontSize: 13, color: "#6e6e73" }}>Loading…</div>;

  return (
    <div>
      <div className="section-card" style={{ overflow: "auto", marginBottom: 16 }}>
        <div className="section-card-header">
          <div className="section-card-title">Policies</div>
        </div>
        <div className="section-card-body" style={{ paddingTop: 0 }}>
          <table className="apple-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Action</th>
                <th>Type</th>
                <th>Config</th>
                <th>Enabled</th>
              </tr>
            </thead>
            <tbody>
              {(policies || []).map((p: { id: number; name: string; action: string; policy_type: string; rule_config: Record<string, unknown>; enabled: boolean }) => (
                <tr key={p.id}>
                  <td style={{ color: "#aeaeb2" }}>{p.id}</td>
                  <td style={{ fontWeight: 500 }}>{p.name}</td>
                  <td><span className={`badge ${p.action === "block" ? "red" : p.action === "flag" ? "orange" : "blue"}`}>{p.action}</span></td>
                  <td style={{ color: "#6e6e73" }}>{p.policy_type}</td>
                  <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 150, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{JSON.stringify(p.rule_config)}</td>
                  <td><span className={`status-label ${p.enabled ? "green" : "gray"}`} style={{ fontSize: 12 }}><span className={`status-dot ${p.enabled ? "green" : "gray"}`} />{p.enabled ? "enabled" : "disabled"}</span></td>
                </tr>
              ))}
              {(!policies || policies.length === 0) && <tr><td colSpan={6} style={{ textAlign: "center", color: "#aeaeb2", padding: 24 }}>No policies defined.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-card">
        <div className="section-card-header">
          <div className="section-card-title">Test Policy</div>
        </div>
        <div className="section-card-body">
          <div className="flex gap-3" style={{ marginBottom: 8 }}>
            <select value={testPolicyId} onChange={(e) => setTestPolicyId(e.target.value)} className="input" style={{ flex: 1 }}>
              <option value="">Select policy</option>
              {(policies || []).map((p: { id: number; name: string }) => (<option key={p.id} value={p.id}>{p.name}</option>))}
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

function EscalationRulesPanel() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const [escalationError, setEscalationError] = useState<string | null>(null);
  const { data: rules, isLoading } = useQuery({ queryKey: ["escalation-rules"], queryFn: fetchEscalationRules });
  const createMut = useMutation({
    mutationFn: (d: { name: string; rule_type: string; rule_config: Record<string, unknown>; target_role: string; description?: string }) => createEscalationRule(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["escalation-rules"] }); setShowForm(false); },
    onError: (err) => { setEscalationError(String(err)); setTimeout(() => setEscalationError(null), 3000); },
  });
  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteEscalationRule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["escalation-rules"] }),
    onError: (err) => { setEscalationError(String(err)); setTimeout(() => setEscalationError(null), 3000); },
  });

  if (isLoading) return <div style={{ fontSize: 13, color: "#6e6e73" }}>Loading…</div>;

  return (
    <div>
      <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
        <p style={{ fontSize: 13, color: "#6e6e73" }}>Escalation rules for flagged content</p>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary btn-sm">+ Add Rule</button>
      </div>
      {escalationError && <div style={{ color: "#ff3b30", fontSize: 12, marginBottom: 8 }}>{escalationError}</div>}

      {showForm && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header">
            <div className="section-card-title">New Escalation Rule</div>
          </div>
          <div className="section-card-body">
            <form onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              const rawConfig = fd.get("rule_config") as string;
              let rule_config: Record<string, unknown>;
              try { rule_config = JSON.parse(rawConfig); } catch { rule_config = { pattern: rawConfig }; }
              createMut.mutate({ name: fd.get("name") as string, rule_type: fd.get("rule_type") as string, rule_config, target_role: fd.get("target_role") as string, description: (fd.get("description") as string) || undefined });
            }} className="flex flex-col gap-3">
              <div className="flex gap-3">
                <input name="name" placeholder="Rule name" className="input" style={{ flex: 1 }} required />
                <select name="rule_type" className="input" style={{ flex: 1 }} required>
                  <option value="keyword">keyword</option>
                  <option value="regex">regex</option>
                  <option value="cost_threshold">cost_threshold</option>
                  <option value="latency_threshold">latency_threshold</option>
                </select>
                <input name="rule_config" placeholder='Config (e.g. {"pattern":"..."})' className="input" style={{ flex: 1 }} required />
                <select name="target_role" className="input" style={{ flex: 1 }} required>
                  <option value="admin">admin</option>
                  <option value="manager">manager</option>
                  <option value="reviewer">reviewer</option>
                </select>
              </div>
              <input name="description" placeholder="Optional description" className="input" />
              <div className="flex gap-2">
                <button type="submit" className="btn btn-primary btn-sm" disabled={createMut.isPending}>{createMut.isPending ? "Creating…" : "Create Rule"}</button>
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
              <th>ID</th>
              <th>Type</th>
              <th>Config</th>
              <th>Target Role</th>
              <th>Description</th>
              <th style={{ textAlign: "center" }}>Delete</th>
            </tr>
          </thead>
          <tbody>
            {(rules || []).map((r: { id: number; rule_type: string; rule_config: Record<string, unknown>; target_role: string; description: string | null }) => (
              <tr key={r.id}>
                <td style={{ color: "#aeaeb2" }}>{r.id}</td>
                <td><span className="badge blue">{r.rule_type}</span></td>
                <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6e6e73", maxWidth: 160 }} className="truncate">{JSON.stringify(r.rule_config)}</td>
                <td style={{ color: "#6e6e73" }}>{r.target_role}</td>
                <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 200 }}>{r.description || "—"}</td>
                <td style={{ textAlign: "center" }}>
                  <button onClick={() => deleteMut.mutate(r.id)} className="btn btn-danger btn-sm" style={{ padding: "2px 8px", fontSize: 11 }}>Delete</button>
                </td>
              </tr>
            ))}
            {(!rules || rules.length === 0) && <tr><td colSpan={6} style={{ textAlign: "center", color: "#aeaeb2", padding: 24 }}>No escalation rules defined.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
