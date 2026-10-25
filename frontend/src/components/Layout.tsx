import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Route, Bell, DollarSign, Eye, Shield, Settings, LogOut,
  Menu, X, Key, FolderKanban, Users, Webhook, GitCompare, Radar, CheckCircle2,
} from "lucide-react";

const navSections = [
  {
    title: "Observe",
    items: [
      { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/traces", icon: Route, label: "Traces & Runs" },
      { to: "/projects", icon: FolderKanban, label: "Projects" },
      { to: "/compare", icon: GitCompare, label: "Compare" },
      { to: "/costs", icon: DollarSign, label: "Costs" },
      { to: "/alerts", icon: Bell, label: "Alerts" },
    ],
  },
  {
    title: "Govern",
    items: [
      { to: "/oversight", icon: Eye, label: "Oversight" },
      { to: "/governance", icon: Shield, label: "Governance" },
    ],
  },
  {
    title: "Workspace",
    items: [
      { to: "/teams", icon: Users, label: "Teams" },
      { to: "/api-keys", icon: Key, label: "API Keys" },
      { to: "/webhooks", icon: Webhook, label: "Webhooks" },
      { to: "/settings", icon: Settings, label: "Settings" },
    ],
  },
];

function Brand() {
  return (
    <div className="sidebar-brand">
      <span className="brand-mark"><Radar size={16} strokeWidth={2.2} /></span>
      <span>
        SBN <span className="brand-sub">· ARMS</span>
      </span>
    </div>
  );
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  const [apiKey, setApiKey] = useState(() => localStorage.getItem("sbn_api_key") || "");
  const [keyEditing, setKeyEditing] = useState(false);

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

  const navContent = (
    <>
      <Brand />
      {navSections.map((section) => (
        <div key={section.title}>
          <div className="sidebar-section">{section.title}</div>
          <div className="sidebar-nav">
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={`sidebar-link ${isActive(item.to) ? "active" : ""}`}
                onClick={() => setMobileOpen(false)}
              >
                <item.icon size={17} strokeWidth={1.8} />
                {item.label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </>
  );

  const accountFooter = (
    <div className="sidebar-footer">
      {keyEditing ? (
        <div style={{ padding: "4px 10px" }}>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk-..."
            className="input"
            style={{ fontSize: 12, minHeight: 30, padding: "5px 10px", marginBottom: 6 }}
            autoFocus
            onKeyDown={(e) => { if (e.key === "Enter") handleKeySave(); }}
          />
          <div className="flex gap-1">
            <button onClick={handleKeySave} className="btn btn-primary btn-sm">Save</button>
            <button onClick={() => setKeyEditing(false)} className="btn btn-secondary btn-sm">Cancel</button>
          </div>
        </div>
      ) : (
        <div className="sidebar-link" onClick={() => setKeyEditing(true)}>
          <CheckCircle2 size={16} strokeWidth={1.8} style={{ color: "var(--green)" }} />
          <span className="flex-1">API key connected</span>
        </div>
      )}
      <div className="sidebar-link" onClick={disconnect}>
        <LogOut size={16} strokeWidth={1.8} />
        Disconnect
      </div>
    </div>
  );

  return (
    <div className="flex" style={{ height: "100vh", overflow: "hidden" }}>
      {/* Desktop sidebar — frosted glass */}
      <nav className="sidebar">
        {navContent}
        {accountFooter}
      </nav>

      {/* Mobile header — frosted glass */}
      <header className="mobile-header">
        <button className="icon-btn" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
          <Menu size={20} strokeWidth={1.8} />
        </button>
        <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-0.02em" }}>SBN · ARMS</span>
        <div style={{ width: 32 }} />
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <>
          <div className="drawer-backdrop" onClick={() => setMobileOpen(false)} />
          <div className="mobile-drawer">
            <div className="flex items-center justify-between" style={{ paddingRight: 4 }}>
              <Brand />
              <button className="icon-btn" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                <X size={18} strokeWidth={1.8} />
              </button>
            </div>
            {navContent}
            {accountFooter}
          </div>
        </>
      )}

      {/* Content */}
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
