import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchRecentTraces, fetchProjects, exportTraces } from "../lib/api";
import { formatCost, formatLatency, formatTime } from "../lib/utils";
import { Download, ChevronLeft, ChevronRight } from "lucide-react";
import SkeletonTable from "../components/SkeletonTable";
import type { RecentTrace } from "../lib/api";

const PAGE_SIZE = 50;

function TableView({
  traces, search, page, onPageChange, onNavigate,
}: {
  traces: RecentTrace[];
  search: string;
  page: number;
  onPageChange: (page: number) => void;
  onNavigate: (id: string) => void;
}) {
  const filtered = traces.filter((t) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (t.request_id || "").toLowerCase().includes(q) || (t.prompt_preview || "").toLowerCase().includes(q) || (t.project_name || "").toLowerCase().includes(q);
  });

  return (
    <div className="section-card" style={{ overflow: "auto" }}>
      <table className="apple-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Project</th>
            <th>Model</th>
            <th>Status</th>
            <th style={{ textAlign: "right" }}>Latency</th>
            <th style={{ textAlign: "right" }}>Tokens</th>
            <th style={{ textAlign: "right" }}>Cost</th>
            <th>Prompt</th>
            <th>Response</th>
          </tr>
        </thead>
        <tbody>
          {filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map((t) => (
            <tr key={t.request_id} onClick={() => onNavigate(t.request_id)}>
              <td style={{ color: "#aeaeb2", fontSize: 12 }}>{formatTime(t.timestamp)}</td>
              <td style={{ fontWeight: 500 }}>{t.project_name}</td>
              <td style={{ color: "#6e6e73" }}>{t.model_name}</td>
              <td><span className={`status-label ${t.status === "success" ? "green" : "red"}`} style={{ fontSize: 12 }}><span className={`status-dot ${t.status === "success" ? "green" : "red"}`} />{t.status}</span></td>
              <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{formatLatency(t.latency_ms)}</td>
              <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{t.total_tokens}</td>
              <td style={{ textAlign: "right", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6e6e73" }}>{formatCost(t.cost)}</td>
              <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 200, fontSize: 12 }}>{t.prompt_preview}</td>
              <td className="truncate" style={{ color: "#aeaeb2", maxWidth: 200, fontSize: 12 }}>{t.response_preview}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={9} style={{ textAlign: "center", color: "#aeaeb2", padding: 32 }}>{search ? "No matching traces" : "No traces yet"}</td></tr>
          )}
        </tbody>
      </table>
      {filtered.length > PAGE_SIZE && (
        <PageFooter count={filtered.length} page={page} onPageChange={onPageChange} />
      )}
    </div>
  );
}

function PageFooter({ count, page, onPageChange }: { count: number; page: number; onPageChange: (page: number) => void }) {
  const totalPages = Math.ceil(count / PAGE_SIZE);

  return (
    <div className="flex items-center justify-between" style={{ padding: "12px 16px", borderTop: "1px solid #e8e8ed" }}>
      <span style={{ fontSize: 12, color: "#aeaeb2" }}>{count} traces</span>
      <div className="flex items-center gap-2">
        <button onClick={() => onPageChange(Math.max(0, page - 1))} disabled={page === 0} className="btn btn-secondary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 2 }}>
          <ChevronLeft size={12} /> Prev
        </button>
        <span style={{ fontSize: 12, color: "#6e6e73" }}>Page {page + 1} of {totalPages}</span>
        <button onClick={() => onPageChange(page + 1)} disabled={(page + 1) * PAGE_SIZE >= count} className="btn btn-secondary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 2 }}>
          Next <ChevronRight size={12} />
        </button>
      </div>
    </div>
  );
}

export default function Traces() {
  const navigate = useNavigate();
  const [projectFilter, setProjectFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [exportFormat, setExportFormat] = useState<"csv" | "json">("json");
  const [exportRedact, setExportRedact] = useState(false);
  const [exporting, setExporting] = useState(false);

  const { data: projects } = useQuery({ queryKey: ["projects"], queryFn: fetchProjects });
  const { data: traces, isLoading } = useQuery({
    queryKey: ["traces", projectFilter || undefined],
    queryFn: () => fetchRecentTraces(200, projectFilter || undefined),
    refetchInterval: 10_000,
  });

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportTraces(exportFormat, projectFilter || undefined, exportRedact);
    } catch (err) { alert("Export failed: " + err); }
    setExporting(false);
  };

  const allTraces = traces || [];

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Traces and Runs</h1>
        <div className="flex items-center gap-2">
          <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as "csv" | "json")} className="input" style={{ width: "auto", fontSize: 11, padding: "4px 8px" }}>
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
          </select>
          <label className="flex items-center gap-1" style={{ fontSize: 11, color: "#6e6e73", cursor: "pointer" }}>
            <input type="checkbox" checked={exportRedact} onChange={(e) => setExportRedact(e.target.checked)} style={{ accentColor: "#0071e3" }} />
            Redact
          </label>
          <button onClick={handleExport} disabled={exporting} className="btn btn-primary btn-sm" style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
            <Download size={12} /> {exporting ? "Exporting\u2026" : "Export"}
          </button>
        </div>
      </div>
      <p className="page-subtitle">Browse and inspect all agent execution traces</p>

      <div className="flex items-center gap-3" style={{ marginBottom: 20 }}>
        <input type="text" placeholder="Search by ID, prompt, or project\u2026" value={search} onChange={(e) => setSearch(e.target.value)} className="input" style={{ maxWidth: 280, fontSize: 13 }} />
        <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)} className="input" style={{ width: "auto", minWidth: 120, fontSize: 12 }}>
          <option value="">All Projects</option>
          {projects?.map((p) => (<option key={p.name} value={p.name}>{p.name}</option>))}
        </select>
      </div>

      {isLoading ? (
        <SkeletonTable rows={10} cols={9} />
      ) : (
        <TableView traces={allTraces} search={search} page={page} onPageChange={setPage} onNavigate={(id) => navigate(`/traces/${id}`)} />
      )}
    </div>
  );
}
