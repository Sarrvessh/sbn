import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Route, Bell, DollarSign, Eye, Shield, Settings, LogOut, Menu, X, Key, FolderKanban, Users, Webhook, GitCompare
} from "lucide-react";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/traces", icon: Route, label: "Traces & Runs" },
  { to: "/projects", icon: FolderKanban, label: "Projects" },
  { to: "/alerts", icon: Bell, label: "Alerts" },
  { to: "/compare", icon: GitCompare, label: "Compare" },
  { to: "/costs", icon: DollarSign, label: "Costs" },
  { to: "/api-keys", icon: Key, label: "API Keys" },
  { to: "/webhooks", icon: Webhook, label: "Webhooks" },
  { to: "/oversight", icon: Eye, label: "Oversight" },
  { to: "/teams", icon: Users, label: "Teams" },
  { to: "/governance", icon: Shield, label: "Governance" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  const [apiKey, setApiKey] = useState(() => localStorage.getItem("sbn_api_key") || "");
  const [keyEditing, setKeyEditing] = useState(!apiKey);

  const handleKeySave = () => {
    const trimmed = apiKey.trim();
    if (trimmed) localStorage.setItem("sbn_api_key", trimmed);
    setKeyEditing(false);
  };

  const disconnect = () => {
    localStorage.removeItem("sbn_api_key");
    setApiKey("");
    window.location.reload();
  };

  const sidebarLinkStyle = (path: string): React.CSSProperties => ({
    display: "flex", alignItems: "center", gap: 10, padding: "6px 12px", borderRadius: 6,
    fontSize: 13, fontWeight: 500, textDecoration: "none", cursor: "pointer",
    color: isActive(path) ? "#ffffff" : "#6e6e73",
    background: isActive(path) ? "#0071e3" : "transparent",
    transition: "all 0.12s ease",
  });

  const sidebarContent = (
    <>
      <div className="sidebar-brand">SBN <span style={{ fontWeight: 400, color: "#aeaeb2" }}>- ARMS</span></div>

      <div className="sidebar-section"></div>
      <div className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} style={sidebarLinkStyle(item.to)}>
            <item.icon size={16} />
            {item.label}
          </NavLink>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-section" style={{ marginTop: 0 }}>Account</div>
        {keyEditing ? (
          <div style={{ padding: "6px 12px" }}>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="input"
              style={{ fontSize: 11, padding: "5px 8px", marginBottom: 4 }}
              autoFocus
            />
            <div className="flex gap-1">
              <button onClick={handleKeySave} className="btn btn-primary btn-sm">Save</button>
              {localStorage.getItem("sbn_api_key") && (
                <button onClick={disconnect} className="btn btn-secondary btn-sm">Disconnect</button>
              )}
            </div>
          </div>
        ) : (
          <div
            className="sidebar-link"
            onClick={() => setKeyEditing(true)}
            style={{ color: "#6e6e73", fontSize: 12 }}
          >
            <Key size={14} />
            {apiKey ? "API Key Set" : "Set API Key"}
          </div>
        )}
        <div className="sidebar-link" onClick={disconnect} style={{ color: "#6e6e73", fontSize: 12, marginTop: 0 }}>
          <LogOut size={14} />
          Disconnect
        </div>
      </div>
    </>
  );

  return (
    <div className="flex" style={{ height: "100vh", overflow: "hidden" }}>
      {/* Desktop sidebar */}
      <nav className="sidebar">{sidebarContent}</nav>

      {/* Mobile header */}
      <header
        className="flex items-center justify-between"
        style={{ display: "none", padding: "12px 16px", background: "#ffffff", borderBottom: "1px solid #d2d2d7" }}
      >
        <button onClick={() => setMobileOpen(!mobileOpen)} style={{ background: "none", border: "none", cursor: "pointer", color: "#1d1d1f" }}>
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <span style={{ fontWeight: 700, fontSize: 15 }}>SBN - ARMS</span>
        <div style={{ width: 20 }} />
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="flex" style={{ position: "fixed", inset: 0, zIndex: 50 }} onClick={() => setMobileOpen(false)}>
          <div style={{ width: 240, background: "#ffffff", borderRight: "1px solid #d2d2d7", padding: "12px 8px" }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#1d1d1f", padding: "8px 12px", marginBottom: 8 }}>SBN — ARMS</div>
            {navItems.map((item) => (
              <NavLink
                key={item.to} to={item.to} onClick={() => setMobileOpen(false)}
                style={{
                  ...sidebarLinkStyle(item.to),
                  borderRadius: 6, padding: "8px 12px",
                }}
              >
                <item.icon size={16} /> {item.label}
              </NavLink>
            ))}
          </div>
          <div style={{ flex: 1 }} />
        </div>
      )}

      {/* Content */}
      <main style={{ flex: 1, height: "100vh", overflowY: "auto", background: "#f5f5f7" }}>
        <Outlet />
      </main>
    </div>
  );
}
