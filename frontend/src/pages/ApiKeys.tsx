import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApiKeys, createApiKey, fetchProjects } from "../lib/api";
import { formatTime } from "../lib/utils";
import { useState } from "react";
import { Plus, Copy, Check } from "lucide-react";

export default function ApiKeys() {
  const queryClient = useQueryClient();
  const { data: keys } = useQuery({ queryKey: ["api-keys"], queryFn: fetchApiKeys });
  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });

  const [showForm, setShowForm] = useState(false);
  const [newRole, setNewRole] = useState("analyst");
  const [newScope, setNewScope] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const createMut = useMutation({
    mutationFn: () => createApiKey({ role: newRole, project_scope: newScope || undefined, description: newDesc.trim() || undefined }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      setCreatedKey(data.api_key);
      setNewRole("analyst"); setNewScope(""); setNewDesc("");
    },
  });

  const handleCopy = async () => {
    if (createdKey) {
      await navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">API Keys</h1>
        <button onClick={() => { setShowForm(!showForm); setCreatedKey(null); }} className="btn btn-primary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
          <Plus size={12} /> {showForm ? "Cancel" : "New Key"}
        </button>
      </div>
      <p className="page-subtitle">Manage API keys for programmatic access</p>

      {showForm && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header"><div className="section-card-title">Create API Key</div></div>
          <div className="section-card-body">
            {createdKey ? (
              <div>
                <div className="alert-banner info" style={{ marginBottom: 12 }}>
                  <strong>Key created!</strong> Copy it now — you won't see it again.
                </div>
                <div className="flex items-center gap-2">
                  <code className="code-block" style={{ flex: 1, padding: "8px 12px", fontSize: 12, wordBreak: "break-all" }}>{createdKey}</code>
                  <button onClick={handleCopy} className="btn btn-primary btn-sm" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
                <button onClick={() => { setCreatedKey(null); setShowForm(false); }} className="btn btn-secondary btn-sm" style={{ marginTop: 8 }}>Done</button>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex gap-3">
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Role</label>
                    <select value={newRole} onChange={(e) => setNewRole(e.target.value)} className="input" style={{ width: "100%" }}>
                      <option value="admin">admin</option>
                      <option value="analyst">analyst</option>
                      <option value="viewer">viewer</option>
                      <option value="ingest">ingest</option>
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Project Scope (optional)</label>
                    <select value={newScope} onChange={(e) => setNewScope(e.target.value)} className="input" style={{ width: "100%" }}>
                      <option value="">All Projects</option>
                      {projects?.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Description</label>
                  <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} className="input" placeholder="CI/CD pipeline key" style={{ width: "100%" }} />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => createMut.mutate()} disabled={createMut.isPending} className="btn btn-primary btn-sm">{createMut.isPending ? "Creating…" : "Create Key"}</button>
                </div>
                {createMut.isError && <p style={{ fontSize: 11, color: "#ff3b30" }}>{(createMut.error as Error)?.message}</p>}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="section-card" style={{ overflow: "auto" }}>
        <table className="apple-table">
          <thead>
            <tr>
              <th>Key Prefix</th>
              <th>Role</th>
              <th>Scope</th>
              <th>Description</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {!keys || keys.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>No API keys created yet.</td></tr>
            ) : (
              keys.map((k) => (
                <tr key={k.key_prefix}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>{k.key_prefix}...</td>
                  <td><span className="badge blue">{k.role}</span></td>
                  <td style={{ color: "#6e6e73", fontSize: 12 }}>{k.project_scope || "—"}</td>
                  <td style={{ color: "#6e6e73", fontSize: 12 }}>{k.description || "—"}</td>
                  <td><span className={`status-label ${k.is_active ? "green" : "gray"}`} style={{ fontSize: 11 }}><span className={`status-dot ${k.is_active ? "green" : "gray"}`} />{k.is_active ? "active" : "inactive"}</span></td>
                  <td style={{ color: "#aeaeb2", fontSize: 12 }}>{formatTime(k.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
