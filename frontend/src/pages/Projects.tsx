import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchProjects, deleteProject, createProject } from "../lib/api";
import { formatTime } from "../lib/utils";
import { Trash2, Plus } from "lucide-react";
import { useState } from "react";

export default function Projects() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });
  const [deleting, setDeleting] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const createMut = useMutation({
    mutationFn: () => createProject(newName.trim(), newDesc.trim() || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setNewName(""); setNewDesc(""); setShowForm(false);
    },
  });

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete project "${name}" and all its traces?`)) return;
    setDeleting(name);
    try {
      await deleteProject(name);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    } catch { }
    setDeleting(null);
  };

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Projects</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
          <Plus size={12} />
          {showForm ? "Cancel" : "New Project"}
        </button>
      </div>
      <p className="page-subtitle">View and manage all projects</p>

      {showForm && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header">
            <div className="section-card-title">Create Project</div>
          </div>
          <div className="section-card-body" style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Project Name</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="input"
                placeholder="my-project"
                style={{ width: "100%" }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Description (optional)</label>
              <input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                className="input"
                placeholder="My project description"
                style={{ width: "100%" }}
              />
            </div>
            <button
              onClick={() => createMut.mutate()}
              disabled={!newName.trim() || createMut.isPending}
              className="btn btn-primary btn-sm"
              style={{ fontSize: 11, height: 34 }}
            >
              {createMut.isPending ? "Creating…" : "Create"}
            </button>
          </div>
          {createMut.isError && (
            <p style={{ fontSize: 11, color: "#ff3b30", margin: "4px 12px 8px" }}>{(createMut.error as Error)?.message || "Failed to create"}</p>
          )}
        </div>
      )}

      <div className="section-card" style={{ overflow: "auto" }}>
        <table className="apple-table">
          <thead>
            <tr>
              <th>Project Name</th>
              <th>Description</th>
              <th>Created</th>
              <th>Models Used</th>
              <th style={{ textAlign: "right" }}>Total Tokens</th>
              <th style={{ textAlign: "right" }}>Traces</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>Loading…</td></tr>
            ) : (projects || []).length === 0 ? (
              <tr><td colSpan={7} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>No projects yet.</td></tr>
            ) : (
              (projects || []).map((p) => (
                <tr key={p.name} onClick={() => navigate(`/projects/${encodeURIComponent(p.name)}`)} style={{ cursor: "pointer" }}>
                  <td style={{ fontWeight: 500 }}>{p.name}</td>
                  <td style={{ color: "#6e6e73", fontSize: 12, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{p.description || "—"}</td>
                  <td style={{ color: "#aeaeb2", fontSize: 12 }}>{formatTime(p.created_at)}</td>
                  <td style={{ color: "#6e6e73", fontSize: 12 }}>{(p.models_used || []).join(", ") || "—"}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{p.total_tokens}</td>
                  <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{p.total_traces}</td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(p.name); }}
                      disabled={deleting === p.name}
                      className="btn btn-danger btn-sm"
                      style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 4 }}
                    >
                      <Trash2 size={12} />
                      {deleting === p.name ? "..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
