import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Traces from "./pages/Traces";
import TraceDetail from "./pages/TraceDetail";
import Alerts from "./pages/Alerts";
import Governance from "./pages/Governance";
import Oversight from "./pages/Oversight";
import Costs from "./pages/Costs";
import Settings from "./pages/Settings";
import Projects from "./pages/Projects";
import ProjectDetail from "./pages/ProjectDetail";
import Teams from "./pages/Teams";
import ApiKeys from "./pages/ApiKeys";
import Webhooks from "./pages/Webhooks";
import TraceCompare from "./pages/TraceCompare";
import Login from "./pages/Login";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const key = localStorage.getItem("sbn_api_key");
  if (!key) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const key = localStorage.getItem("sbn_api_key");
  if (key) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<GuestRoute><Login /></GuestRoute>} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/traces" element={<Traces />} />
        <Route path="/traces/:requestId" element={<TraceDetail />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/governance" element={<Governance />} />
        <Route path="/oversight" element={<Oversight />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:projectName" element={<ProjectDetail />} />
        <Route path="/costs" element={<Costs />} />
        <Route path="/teams" element={<Teams />} />
        <Route path="/api-keys" element={<ApiKeys />} />
        <Route path="/webhooks" element={<Webhooks />} />
        <Route path="/compare" element={<TraceCompare />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
