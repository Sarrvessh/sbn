const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export function getHeaders(apiKey?: string): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;
  return headers;
}

export function getApiKey(): string {
  return localStorage.getItem("sbn_api_key") || "";
}

function apiKeyHeaders(): Record<string, string> {
  return getHeaders(getApiKey());
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...apiKeyHeaders(), ...options?.headers },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface RealtimeMetrics {
  total_cost: number;
  average_latency_last_50_ms: number;
  p95_latency_last_50_ms: number;
  governance_flagged_count: number;
  error_rate_last_50_percent: number;
  traces_last_24h: number;
}

export interface GovernanceMetrics {
  total_traces: number;
  total_flagged: number;
  flag_rate: number;
  pending_reviews: number;
  approved_reviews: number;
  rejected_reviews: number;
  by_severity: { severity: string; count: number }[];
  recent_flags: { request_id: string; project_name: string; model_name: string; timestamp: string | null; status: string }[];
}

export interface RecentTrace {
  request_id: string;
  project_name: string;
  model_name: string;
  total_tokens: number;
  cost: number;
  latency_ms: number;
  status: "success" | "error";
  flagged_for_governance: boolean;
  prompt_preview: string;
  response_preview: string;
  timestamp: string;
}

export interface TraceSpan {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  trace_request_id: string;
  name: string;
  kind: string;
  span_type: string;
  input: string | null;
  output: string | null;
  tool_name: string | null;
  model_name: string | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  attributes: Record<string, unknown> | null;
  retrieval_documents?: { id: string; content: string; score?: number; source?: string }[];
  status_code: string;
  status_message: string | null;
  started_at: string;
  ended_at: string | null;
  created_at: string;
}

export interface TraceDetail {
  request_id: string;
  project_name: string;
  prompt: string;
  response: string;
  model_name: string;
  total_tokens: number;
  cost: number;
  latency_ms: number;
  status: "success" | "error";
  flagged_for_governance: boolean;
  timestamp: string;
  spans: TraceSpan[];
}

export interface Alert {
  request_id: string;
  project_name: string;
  severity: "low" | "medium" | "high";
  alert_type: "high_latency" | "high_cost" | "governance" | "execution_error";
  message: string;
  latency_ms: number;
  cost: number;
  status: "success" | "error";
  timestamp: string;
}

export async function fetchGovernanceMetrics(project?: string): Promise<GovernanceMetrics> {
  const params = project ? `?project_name=${encodeURIComponent(project)}` : "";
  return request<GovernanceMetrics>(`/api/v1/analytics/governance${params}`);
}

export async function fetchMetrics(project?: string): Promise<RealtimeMetrics> {
  const params = project ? `?project_name=${encodeURIComponent(project)}` : "";
  return request<RealtimeMetrics>(`/api/v1/analytics/realtime${params}`);
}

export async function fetchRecentTraces(
  limit = 100,
  project?: string
): Promise<RecentTrace[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (project) params.set("project_name", project);
  return request<RecentTrace[]>(`/api/v1/traces/recent?${params}`);
}

export async function fetchTraceDetail(
  requestId: string, redact: boolean = false
): Promise<TraceDetail> {
  const params = redact ? "?redact=true" : "";
  return request<TraceDetail>(`/api/v1/traces/${requestId}${params}`);
}

export async function fetchAlerts(
  limit = 50,
  project?: string
): Promise<Alert[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (project) params.set("project_name", project);
  return request<Alert[]>(`/api/v1/alerts?${params}`);
}

export interface ProjectInfo {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  total_tokens: number;
  total_traces: number;
  models_used: string[];
}

export interface ProjectDetail {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  total_tokens: number;
  total_cost: number;
  total_traces: number;
  success_rate: number;
  average_latency_ms: number;
  models_used: string[];
  first_trace_at: string | null;
}

export async function fetchProjects(): Promise<ProjectInfo[]> {
  return request<ProjectInfo[]>("/api/v1/projects");
}

export async function fetchProjectDetail(name: string): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/api/v1/projects/${encodeURIComponent(name)}`);
}

export async function createProject(name: string, description?: string): Promise<ProjectInfo> {
  return request<ProjectInfo>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}

// ─── System Metrics ───
export interface SystemMetrics {
  total_traces: number;
  total_projects: number;
  error_rate: number;
  average_latency_ms: number;
  total_tokens: number;
  total_cost: number;
  unique_models: string[];
  traces_today: number;
  uptime_hours: number;
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  return request<SystemMetrics>("/api/v1/analytics/system");
}

// ─── Webhooks ───
export interface WebhookInfo {
  id: number;
  name: string;
  url: string;
  secret: string | null;
  events: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookDelivery {
  id: number;
  webhook_id: number;
  event_type: string;
  payload: Record<string, unknown>;
  status: string;
  status_code: number | null;
  response_body: string | null;
  delivered_at: string;
}

export async function fetchWebhooks(): Promise<WebhookInfo[]> {
  return request<WebhookInfo[]>("/api/v1/webhooks");
}

export async function createWebhook(payload: { name: string; url: string; secret?: string; events: string[]; enabled?: boolean }): Promise<WebhookInfo> {
  return request<WebhookInfo>("/api/v1/webhooks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateWebhook(id: number, payload: Record<string, unknown>): Promise<WebhookInfo> {
  return request<WebhookInfo>(`/api/v1/webhooks/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteWebhook(id: number): Promise<void> {
  await request<void>(`/api/v1/webhooks/${id}`, { method: "DELETE" });
}

export async function fetchWebhookDeliveries(webhookId: number, limit = 20): Promise<WebhookDelivery[]> {
  return request<WebhookDelivery[]>(`/api/v1/webhooks/${webhookId}/deliveries?limit=${limit}`);
}

export async function testWebhook(url: string, secret?: string): Promise<{ success: boolean; status_code: number | null; response_body: string | null; error?: string }> {
  return request("/api/v1/webhooks/test", {
    method: "POST",
    body: JSON.stringify({ url, secret }),
  });
}

// ─── Export ───
export async function exportTraces(format: "csv" | "json", project?: string, redact?: boolean): Promise<void> {
  const params = new URLSearchParams({ format });
  if (project) params.set("project_name", project);
  if (redact) params.set("redact", "true");
  const url = `${BACKEND_URL}/api/v1/export/traces?${params}`;
  const res = await fetch(url, { headers: apiKeyHeaders() });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `traces.${format}`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ─── API Keys ───
export interface ApiKeyInfo {
  key_prefix: string;
  role: string;
  project_scope: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyCreateResponse extends ApiKeyInfo {
  api_key: string;
}

export async function fetchApiKeys(): Promise<ApiKeyInfo[]> {
  return request<ApiKeyInfo[]>("/api/v1/auth/api-keys");
}

export async function createApiKey(payload: { role: string; project_scope?: string; description?: string }): Promise<ApiKeyCreateResponse> {
  return request<ApiKeyCreateResponse>("/api/v1/auth/api-keys", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Cost Prediction ───
export interface CostPrediction {
  projected_monthly_cost: number;
  projected_daily_avg: number;
  confidence: string;
  daily_predictions: { date: string; actual_cost: number | null; predicted_cost: number | null }[];
}

export async function fetchCostPrediction(project?: string): Promise<CostPrediction> {
  const params = project ? `?project_name=${encodeURIComponent(project)}` : "";
  return request<CostPrediction>(`/api/v1/analytics/costs/predicted${params}`);
}

// ─── Teams ───
export interface TeamInfo {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface TeamProjectAssignment {
  id: number;
  team_id: number;
  project_name: string;
}

export interface BudgetInfo {
  id: number;
  team_id: number;
  month: string;
  budget_cents: number;
  created_at: string;
  updated_at: string;
}

export async function fetchTeams(): Promise<TeamInfo[]> {
  return request<TeamInfo[]>("/api/v1/teams");
}

export async function createTeam(name: string, description?: string): Promise<TeamInfo> {
  return request<TeamInfo>("/api/v1/teams", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}

export async function deleteTeam(id: number): Promise<void> {
  await request<void>(`/api/v1/teams/${id}`, { method: "DELETE" });
}

export async function fetchTeamProjects(teamId: number): Promise<TeamProjectAssignment[]> {
  return request<TeamProjectAssignment[]>(`/api/v1/teams/${teamId}/projects`);
}

export async function assignTeamProject(teamId: number, projectName: string): Promise<TeamProjectAssignment> {
  return request<TeamProjectAssignment>(`/api/v1/teams/${teamId}/projects`, {
    method: "POST",
    body: JSON.stringify({ project_name: projectName }),
  });
}

export async function removeTeamProject(teamId: number, projectName: string): Promise<void> {
  await request<void>(`/api/v1/teams/${teamId}/projects?project_name=${encodeURIComponent(projectName)}`, { method: "DELETE" });
}

export async function fetchBudgets(): Promise<BudgetInfo[]> {
  return request<BudgetInfo[]>("/api/v1/budgets");
}

export async function createBudget(teamId: number, month: string, budgetCents: number): Promise<BudgetInfo> {
  return request<BudgetInfo>("/api/v1/budgets", {
    method: "POST",
    body: JSON.stringify({ team_id: teamId, month, budget_cents: budgetCents }),
  });
}

export async function deleteBudget(id: number): Promise<void> {
  await request<void>(`/api/v1/budgets/${id}`, { method: "DELETE" });
}

export async function deleteProject(name: string): Promise<void> {
  await request<void>(`/api/v1/projects/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export interface AlertRule {
  id: number;
  name: string;
  project_name: string | null;
  alert_type: string;
  severity: string;
  threshold_value: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export async function fetchAlertRules(): Promise<AlertRule[]> {
  return request<AlertRule[]>("/api/v1/alert-rules");
}

export async function createAlertRule(payload: {
  name: string;
  project_name?: string;
  alert_type: string;
  severity?: string;
  threshold_value: number;
  enabled?: boolean;
}): Promise<AlertRule> {
  return request<AlertRule>("/api/v1/alert-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAlertRule(id: number, payload: Record<string, unknown>): Promise<AlertRule> {
  return request<AlertRule>(`/api/v1/alert-rules/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteAlertRule(id: number): Promise<void> {
  await request<void>(`/api/v1/alert-rules/${id}`, { method: "DELETE" });
}

export interface EscalationRule {
  id: number;
  name: string;
  description: string | null;
  rule_type: string;
  rule_config: Record<string, unknown>;
  target_role: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export async function fetchEscalationRules(): Promise<EscalationRule[]> {
  return request<EscalationRule[]>("/api/v1/escalation-rules");
}

export async function createEscalationRule(payload: {
  name: string;
  rule_type: string;
  rule_config: Record<string, unknown>;
  target_role: string;
  description?: string;
}): Promise<EscalationRule> {
  return request<EscalationRule>("/api/v1/escalation-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteEscalationRule(id: number): Promise<void> {
  await request<void>(`/api/v1/escalation-rules/${id}`, { method: "DELETE" });
}

export interface Policy {
  id: number;
  name: string;
  description: string | null;
  policy_type: string;
  rule_config: Record<string, unknown>;
  severity: string;
  enabled: boolean;
  action: string;
  project_scope: string | null;
  created_at: string;
  updated_at: string;
}

export async function fetchPolicies(): Promise<Policy[]> {
  return request<Policy[]>("/api/v1/policies");
}

export async function createPolicy(payload: Record<string, unknown>): Promise<Policy> {
  return request<Policy>("/api/v1/policies", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updatePolicy(id: number, payload: Record<string, unknown>): Promise<Policy> {
  return request<Policy>(`/api/v1/policies/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deletePolicy(id: number): Promise<void> {
  await request<void>(`/api/v1/policies/${id}`, { method: "DELETE" });
}

export interface PolicyException {
  id: number;
  policy_id: number;
  pattern: string;
  reason: string | null;
  created_at: string;
}

export async function fetchPolicyExceptions(policyId: number): Promise<PolicyException[]> {
  return request<PolicyException[]>(`/api/v1/policies/${policyId}/exceptions`);
}

export async function createPolicyException(policyId: number, pattern: string, reason?: string): Promise<PolicyException> {
  return request<PolicyException>(`/api/v1/policies/${policyId}/exceptions`, {
    method: "POST",
    body: JSON.stringify({ policy_id: policyId, pattern, reason }),
  });
}

export async function deletePolicyException(exceptionId: number): Promise<void> {
  await request<void>(`/api/v1/exceptions/${exceptionId}`, { method: "DELETE" });
}

export async function evaluatePolicies(
  policyId: string,
  prompt: string
): Promise<{ decision: string; matched_policies: { policy_id: number; policy_name: string; matched: boolean; reason: string | null; action: string }[] }> {
  return request(`/api/v1/policies/${policyId}/evaluate`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export interface ReviewItem {
  request_id: string;
  project_name: string;
  model_name: string;
  total_tokens: number;
  cost: number;
  prompt_preview: string;
  response_preview: string;
  timestamp: string;
}

export async function fetchReviewQueue(redact = false): Promise<ReviewItem[]> {
  const params = redact ? "?redact=true" : "";
  return request<ReviewItem[]>(`/api/v1/reviews/pending${params}`);
}

export async function fetchReviewed(redact = false): Promise<(ReviewItem & { latest_review: { id: number; decision: string; reviewer: string; notes?: string } | null })[]> {
  const params = redact ? "?redact=true" : "";
  return request<(ReviewItem & { latest_review: { id: number; decision: string; reviewer: string; notes?: string } | null })[]>(`/api/v1/reviews/reviewed${params}`);
}

export async function reviewAction(
  requestId: string,
  decision: string,
  notes?: string
): Promise<void> {
  await request<void>("/api/v1/reviews", {
    method: "POST",
    body: JSON.stringify({
      request_id: requestId,
      reviewer: "frontend-user",
      decision,
      notes: notes || null,
    }),
  });
}

export async function flagTrace(requestId: string): Promise<TraceDetail> {
  return request<TraceDetail>(`/api/v1/traces/${requestId}/flag`, { method: "POST" });
}

export async function unflagTrace(requestId: string): Promise<TraceDetail> {
  return request<TraceDetail>(`/api/v1/traces/${requestId}/unflag`, { method: "POST" });
}

export interface CostAnalytics {
  total_cost: number;
  total_tokens: number;
  total_traces: number;
  cost_this_month: number;
  traces_this_month: number;
  daily_costs: { date: string; cost: number; trace_count: number }[];
  by_model: { model_name: string; total_cost: number; total_tokens: number; trace_count: number }[];
  by_project: { project_name: string; total_cost: number; total_tokens: number; trace_count: number }[];
  teams: { name: string; total_cost: number; total_tokens: number; trace_count: number; budget: number }[];
}

export async function fetchCostAnalytics(project?: string): Promise<CostAnalytics> {
  const params = project ? `?project_name=${encodeURIComponent(project)}` : "";
  const raw: any = await request(`/api/v1/analytics/costs${params}`);
  return {
    total_cost: raw.total_cost,
    total_tokens: raw.total_tokens,
    total_traces: raw.total_traces,
    cost_this_month: raw.cost_this_month,
    traces_this_month: raw.traces_this_month,
    daily_costs: raw.daily_costs || [],
    by_model: raw.by_model || [],
    by_project: raw.by_project || [],
    teams: (raw.by_team || []).map((t: any) => ({
      name: t.team_name,
      total_cost: t.total_cost,
      total_tokens: t.total_tokens,
      trace_count: t.trace_count,
      budget: t.budget_cents ? t.budget_cents / 100 : 0,
    })),
  };
}

export interface AppSettings {
  default_agent_model: string;
  max_tokens: number;
  temperature: number;
  sampling_rate: number;
  budget_alert_threshold_pct: number;
  openai_api_key?: string;
  openai_base_url?: string;
  openai_referer?: string;
  openai_app_title?: string;
}

export async function fetchSettings(): Promise<AppSettings> {
  return request<AppSettings>("/api/v1/settings");
}

export async function updateSettings(payload: Record<string, unknown>): Promise<AppSettings> {
  return request<AppSettings>("/api/v1/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function fetchAuditLogs(limit = 50): Promise<{ id: number; actor: string; action: string; resource_type: string; resource_id: string | null; details: Record<string, unknown> | null; created_at: string }[]> {
  return request(`/api/v1/audit-log?limit=${limit}`);
}

export async function runAgent(payload: {
  project_name: string;
  prompt: string;
  model_name?: string;
  max_tokens?: number;
  temperature?: number;
}) {
  return request<{
    request_id: string;
    status: string;
    response: string;
    total_tokens: number;
    cost: number;
    latency_ms: number;
    flagged_for_governance: boolean;
    governance_reasons: string[];
  }>("/api/v1/agent/run", {
    method: "POST",
    body: JSON.stringify({
      project_name: payload.project_name,
      prompt: payload.prompt,
      model_name: payload.model_name || "gpt-4o-mini",
      max_tokens: payload.max_tokens ?? 512,
      temperature: payload.temperature ?? 0.2,
    }),
  });
}
