import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTeams, createTeam, deleteTeam, fetchBudgets, createBudget, deleteBudget, fetchProjects, fetchTeamProjects, assignTeamProject, removeTeamProject } from "../lib/api";
import { formatCost } from "../lib/utils";
import { useState } from "react";
import { Plus, Trash2, Edit3 } from "lucide-react";

const year = new Date().getFullYear();
const MONTHS = Array.from({ length: 12 }, (_, i) => `${String(year)}-${String(i + 1).padStart(2, "0")}`);

export default function Teams() {
  const queryClient = useQueryClient();

  const { data: teams } = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });
  const { data: budgets } = useQuery({ queryKey: ["budgets"], queryFn: fetchBudgets });
  const { data: allProjects } = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });

  // Create team state
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const createMut = useMutation({
    mutationFn: () => createTeam(newName.trim(), newDesc.trim() || undefined),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["teams"] }); setNewName(""); setNewDesc(""); setShowCreate(false); },
  });

  // Budget state
  const [budgetTeam, setBudgetTeam] = useState<number | null>(null);
  const [budgetMonth, setBudgetMonth] = useState(MONTHS[5]);
  const [budgetAmount, setBudgetAmount] = useState("");

  const createBudgetMut = useMutation({
    mutationFn: () => createBudget(budgetTeam!, budgetMonth, Math.round(parseFloat(budgetAmount) * 100)),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["budgets"] }); setBudgetTeam(null); setBudgetAmount(""); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: number) => deleteTeam(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["teams"] }),
  });

  const deleteBudgetMut = useMutation({
    mutationFn: (id: number) => deleteBudget(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["budgets"] }),
  });

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Teams &amp; Budgets</h1>
        <button onClick={() => setShowCreate(!showCreate)} className="btn btn-primary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
          <Plus size={12} /> {showCreate ? "Cancel" : "New Team"}
        </button>
      </div>
      <p className="page-subtitle">Manage teams, assign projects, and set budgets</p>

      {showCreate && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header"><div className="section-card-title">Create Team</div></div>
          <div className="section-card-body" style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Team Name</label>
              <input value={newName} onChange={(e) => setNewName(e.target.value)} className="input" placeholder="engineering" style={{ width: "100%" }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Description</label>
              <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} className="input" placeholder="Engineering team" style={{ width: "100%" }} />
            </div>
            <button onClick={() => createMut.mutate()} disabled={!newName.trim() || createMut.isPending} className="btn btn-primary btn-sm" style={{ height: 34 }}>{createMut.isPending ? "…" : "Create"}</button>
          </div>
        </div>
      )}

      {budgetTeam !== null && (
        <div className="section-card" style={{ marginBottom: 16 }}>
          <div className="section-card-header"><div className="section-card-title">Set Budget</div></div>
          <div className="section-card-body" style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <div>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Month</label>
              <select value={budgetMonth} onChange={(e) => setBudgetMonth(e.target.value)} className="input" style={{ fontSize: 12 }}>
                {MONTHS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Budget ($)</label>
              <input value={budgetAmount} onChange={(e) => setBudgetAmount(e.target.value)} type="number" step="0.01" className="input" placeholder="100.00" style={{ width: 140 }} />
            </div>
            <button onClick={() => createBudgetMut.mutate()} disabled={!budgetAmount || createBudgetMut.isPending} className="btn btn-primary btn-sm" style={{ height: 34 }}>{createBudgetMut.isPending ? "…" : "Save"}</button>
            <button onClick={() => setBudgetTeam(null)} className="btn btn-secondary btn-sm" style={{ height: 34 }}>Cancel</button>
          </div>
        </div>
      )}

      <div className="section-card" style={{ overflow: "auto" }}>
        <table className="apple-table">
          <thead>
            <tr>
              <th>Team</th>
              <th>Description</th>
              <th>Projects</th>
              <th style={{ textAlign: "right" }}>Budget</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {!teams || teams.length === 0 ? (
              <tr><td colSpan={5} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>No teams yet. Create one to get started.</td></tr>
            ) : (
              teams.map((t) => {
                const teamBudgets = (budgets || []).filter((b) => b.team_id === t.id);
                const totalBudget = teamBudgets.reduce((s, b) => s + b.budget_cents, 0);
                return (
                  <tr key={t.id}>
                    <td style={{ fontWeight: 500 }}>{t.name}</td>
                    <td style={{ color: "#6e6e73", fontSize: 12 }}>{t.description || "—"}</td>
                    <td style={{ color: "#6e6e73", fontSize: 12 }}>
                      <TeamProjects teamId={t.id} allProjects={allProjects || []} />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#6e6e73" }}>
                        {totalBudget > 0 ? formatCost(totalBudget / 100) : "—"}
                      </span>
                      <button
                        onClick={() => { setBudgetTeam(t.id); setBudgetAmount(""); }}
                        className="link"
                        style={{ fontSize: 10, marginLeft: 6, background: "none", border: "none", cursor: "pointer" }}
                      >
                        <Edit3 size={11} />
                      </button>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        onClick={() => deleteMut.mutate(t.id)}
                        disabled={deleteMut.isPending}
                        className="btn btn-danger btn-sm"
                        style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 4 }}
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {budgets && budgets.length > 0 && (
        <div className="section-card" style={{ marginTop: 16, overflow: "auto" }}>
          <div className="section-card-header"><div className="section-card-title">All Budgets</div></div>
          <table className="apple-table">
            <thead>
              <tr>
                <th>Team</th>
                <th>Month</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {budgets.map((b) => {
                const teamName = teams?.find((t) => t.id === b.team_id)?.name || `Team #${b.team_id}`;
                return (
                  <tr key={b.id}>
                    <td>{teamName}</td>
                    <td style={{ color: "#6e6e73" }}>{b.month}</td>
                    <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{formatCost(b.budget_cents / 100)}</td>
                    <td style={{ textAlign: "right" }}>
                      <button onClick={() => deleteBudgetMut.mutate(b.id)} className="btn btn-danger btn-sm" style={{ fontSize: 11 }}>
                        <Trash2 size={12} /> Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TeamProjects({ teamId, allProjects }: { teamId: number; allProjects: { name: string }[] }) {
  const { data: assigned } = useQuery({
    queryKey: ["team-projects", teamId],
    queryFn: () => fetchTeamProjects(teamId),
  });
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState("");

  const assignMut = useMutation({
    mutationFn: (projectName: string) => assignTeamProject(teamId, projectName),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["team-projects", teamId] }); setAdding(false); setSelected(""); },
  });

  const removeMut = useMutation({
    mutationFn: (projectName: string) => removeTeamProject(teamId, projectName),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["team-projects", teamId] }),
  });

  const assignedNames = (assigned || []).map((a) => a.project_name);
  const unassigned = allProjects.filter((p) => !assignedNames.includes(p.name));

  return (
    <div>
      {assignedNames.length === 0 ? <span style={{ color: "#aeaeb2" }}>—</span> : assignedNames.join(", ")}
      {adding ? (
        <div className="flex gap-1" style={{ marginTop: 4 }}>
          <select value={selected} onChange={(e) => setSelected(e.target.value)} className="input" style={{ fontSize: 11, padding: "2px 6px", width: "auto" }}>
            <option value="">Select…</option>
            {unassigned.map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
          <button onClick={() => selected && assignMut.mutate(selected)} disabled={!selected} className="btn btn-primary btn-sm" style={{ fontSize: 10, padding: "2px 6px" }}>Add</button>
          <button onClick={() => setAdding(false)} className="btn btn-secondary btn-sm" style={{ fontSize: 10, padding: "2px 6px" }}>X</button>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="link" style={{ fontSize: 10, marginLeft: 4, background: "none", border: "none", cursor: "pointer" }}>+ Assign</button>
      )}
    </div>
  );
}
