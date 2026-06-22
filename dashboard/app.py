"""Realtime Streamlit console for live AI agent observability."""

from __future__ import annotations

import json
import os
from typing import Any

import requests
import streamlit as st
from streamlit.components.v1 import html


DEFAULT_BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
DEFAULT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", "gpt-4o-mini")
DEFAULT_API_KEY = os.getenv("SBN_API_KEY", "admin-local-dev-key")


def _build_url(base_url: str, path: str) -> str:
        """Build endpoint URL from base URL and route path."""

        return f"{base_url.rstrip('/')}{path}"


def _headers(api_key: str) -> dict[str, str]:
        """Build request headers for authenticated API access."""

        return {"X-API-Key": api_key}


def _get_json(
        url: str,
        api_key: str,
        params: dict[str, Any] | None = None,
) -> Any:
        """Fetch JSON payload from backend endpoint."""

        response = requests.get(url, params=params, headers=_headers(api_key), timeout=20)
        response.raise_for_status()
        return response.json()


def _post_json(url: str, api_key: str, payload: dict[str, Any]) -> Any:
        """Send JSON payload to backend endpoint."""

        response = requests.post(url, json=payload, headers=_headers(api_key), timeout=120)
        response.raise_for_status()
        return response.json()


st.set_page_config(page_title="Realtime Agent Analyzer", layout="wide")
st.title("Realtime Agent Analyzer")
st.caption("Event-driven stream with RBAC, API key auth, and project-scoped views")

with st.sidebar:
        st.header("Analyzer Controls")
        backend_base_url = st.text_input("Backend Base URL", value=DEFAULT_BACKEND_BASE_URL)
        api_key = st.text_input("API Key", value=DEFAULT_API_KEY, type="password")
        project_filter = st.text_input("Project Filter (optional)", value="")
        trace_limit = st.slider("Traces to retain", min_value=20, max_value=300, value=100)
        alert_limit = st.slider("Alerts to retain", min_value=10, max_value=150, value=50)

if not api_key.strip():
        st.error("API Key is required. Set one of your bootstrap keys in sidebar.")
        st.stop()

health_url = _build_url(backend_base_url, "/health")
metrics_url = _build_url(backend_base_url, "/api/v1/analytics/realtime")
run_agent_url = _build_url(backend_base_url, "/api/v1/agent/run")

try:
        health = requests.get(health_url, timeout=5).json()
        if health.get("status") == "ok":
                st.success("Backend status: healthy")
        else:
                st.warning("Backend status returned unexpected payload")
except requests.RequestException as exc:
        st.error(f"Backend unreachable: {exc}")
        st.stop()

metrics_params = {"project_name": project_filter} if project_filter.strip() else None
try:
        _get_json(metrics_url, api_key=api_key, params=metrics_params)
except requests.HTTPError as exc:
        details = exc.response.text if exc.response is not None else str(exc)
        st.error(f"Auth/authorization failed: {details}")
        st.stop()
except requests.RequestException as exc:
        st.error(f"Failed to validate API key: {exc}")
        st.stop()

with st.expander("Run Live Agent", expanded=True):
        with st.form("run-agent-form", clear_on_submit=False):
                project_name = st.text_input(
                        "Project Name",
                        value=project_filter.strip() or "resume-star-project",
                )
                model_name = st.text_input("Model Name", value=DEFAULT_MODEL)

                col1, col2 = st.columns(2)
                with col1:
                        max_tokens = st.number_input("Max Output Tokens", min_value=1, max_value=4096, value=512)
                with col2:
                        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.2)

                prompt = st.text_area(
                        "Prompt",
                        placeholder="Enter a real prompt for your model...",
                        height=140,
                )
                run_clicked = st.form_submit_button("Run Agent")

        if run_clicked:
                if not prompt.strip():
                        st.warning("Prompt is required.")
                else:
                        payload = {
                                "project_name": project_name,
                                "prompt": prompt,
                                "model_name": model_name,
                                "max_tokens": int(max_tokens),
                                "temperature": float(temperature),
                        }
                        try:
                                run_result = _post_json(run_agent_url, api_key=api_key, payload=payload)
                                st.success("Agent executed and telemetry published to realtime stream.")
                                st.write(run_result.get("response", ""))

                                telemetry_cols = st.columns(4)
                                telemetry_cols[0].metric("Latency", f"{run_result.get('latency_ms', 0.0):.2f} ms")
                                telemetry_cols[1].metric("Tokens", int(run_result.get("total_tokens", 0)))
                                telemetry_cols[2].metric("Cost", f"${run_result.get('cost', 0.0):.6f}")
                                telemetry_cols[3].metric(
                                        "Governance Flag",
                                        "Yes" if run_result.get("flagged_for_governance") else "No",
                                )

                                reasons = run_result.get("governance_reasons", [])
                                if reasons:
                                        st.warning("Governance triggers: " + " | ".join(str(item) for item in reasons))
                        except requests.HTTPError as exc:
                                details = ""
                                if exc.response is not None:
                                        try:
                                                details = str(exc.response.json())
                                        except ValueError:
                                                details = exc.response.text
                                st.error(f"Agent execution failed: {details or exc}")
                        except requests.RequestException as exc:
                                st.error(f"Backend request failed: {exc}")

st.subheader("Push Stream")
st.info(
        "This panel uses SSE push from backend; updates are event-driven and not polled by Python loops."
)

stream_config = {
        "baseUrl": backend_base_url.rstrip("/"),
        "apiKey": api_key,
        "projectName": project_filter.strip() or None,
        "traceLimit": int(trace_limit),
        "alertLimit": int(alert_limit),
}

html(
        f"""
<div id="sbn-root" style="font-family: Segoe UI, sans-serif;">
    <style>
        .grid {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin-bottom: 12px; }}
        .card {{ border: 1px solid #d0d7de; border-radius: 8px; padding: 8px; background: #f6f8fa; }}
        .title {{ font-size: 12px; color: #57606a; margin-bottom: 3px; }}
        .value {{ font-size: 18px; font-weight: 600; color: #24292f; }}
        .status {{ margin-bottom: 10px; padding: 8px; border-radius: 6px; background: #fff8c5; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        th, td {{ border: 1px solid #d0d7de; padding: 6px; text-align: left; vertical-align: top; }}
        th {{ background: #f6f8fa; position: sticky; top: 0; }}
        .section {{ margin-top: 14px; }}
        .scroll-wrap {{ max-height: 360px; overflow-y: auto; border: 1px solid #d0d7de; border-radius: 8px; }}
    </style>

    <div id="status" class="status">Connecting...</div>
    <div class="grid" id="metrics"></div>

    <div class="section">
        <h4>Alerts</h4>
        <div class="scroll-wrap"><table><thead><tr>
            <th>Timestamp</th><th>Severity</th><th>Type</th><th>Project</th><th>Message</th>
        </tr></thead><tbody id="alerts-body"></tbody></table></div>
    </div>

    <div class="section">
        <h4>Trace Stream</h4>
        <div class="scroll-wrap"><table><thead><tr>
            <th>Timestamp</th><th>Project</th><th>Model</th><th>Status</th><th>Latency</th><th>Tokens</th><th>Cost</th><th>Flagged</th><th>Prompt</th><th>Response</th>
        </tr></thead><tbody id="traces-body"></tbody></table></div>
    </div>
</div>

<script>
const config = {json.dumps(stream_config)};
const state = {{ metrics: null, traces: [], alerts: [] }};

const statusEl = document.getElementById('status');
const metricsEl = document.getElementById('metrics');
const tracesBody = document.getElementById('traces-body');
const alertsBody = document.getElementById('alerts-body');

const authHeaders = () => ({{ 'X-API-Key': config.apiKey }});

function updateStatus(message) {{
    statusEl.textContent = message;
}}

function escapeHtml(value) {{
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}}

function toUrl(path, params) {{
    const url = new URL(config.baseUrl + path);
    if (params) {{
        for (const [key, value] of Object.entries(params)) {{
            if (value !== null && value !== undefined && String(value).length > 0) {{
                url.searchParams.set(key, String(value));
            }}
        }}
    }}
    return url.toString();
}}

function renderMetrics(metrics) {{
    if (!metrics) return;
    const items = [
        ['Total Cost', `$${{Number(metrics.total_cost || 0).toFixed(4)}}`],
        ['Avg Latency (50)', `${{Number(metrics.average_latency_last_50_ms || 0).toFixed(2)}} ms`],
        ['P95 Latency (50)', `${{Number(metrics.p95_latency_last_50_ms || 0).toFixed(2)}} ms`],
        ['Error Rate (50)', `${{Number(metrics.error_rate_last_50_percent || 0).toFixed(2)}}%`],
        ['Governance Flags', String(metrics.governance_flagged_count || 0)],
        ['Traces (24h)', String(metrics.traces_last_24h || 0)],
    ];

    metricsEl.innerHTML = items
        .map(([title, value]) => `<div class="card"><div class="title">${{escapeHtml(title)}}</div><div class="value">${{escapeHtml(value)}}</div></div>`)
        .join('');
}}

function renderAlerts(alerts) {{
    alertsBody.innerHTML = alerts
        .slice(0, config.alertLimit)
        .map((alert) => `
            <tr>
                <td>${{escapeHtml(alert.timestamp)}}</td>
                <td>${{escapeHtml(alert.severity)}}</td>
                <td>${{escapeHtml(alert.alert_type)}}</td>
                <td>${{escapeHtml(alert.project_name)}}</td>
                <td>${{escapeHtml(alert.message)}}</td>
            </tr>
        `)
        .join('');
}}

function renderTraces(traces) {{
    tracesBody.innerHTML = traces
        .slice(0, config.traceLimit)
        .map((trace) => `
            <tr>
                <td>${{escapeHtml(trace.timestamp)}}</td>
                <td>${{escapeHtml(trace.project_name)}}</td>
                <td>${{escapeHtml(trace.model_name)}}</td>
                <td>${{escapeHtml(trace.status)}}</td>
                <td>${{escapeHtml(Number(trace.latency_ms || 0).toFixed(2))}}</td>
                <td>${{escapeHtml(trace.total_tokens)}}</td>
                <td>${{escapeHtml(Number(trace.cost || 0).toFixed(6))}}</td>
                <td>${{escapeHtml(trace.flagged_for_governance ? 'Yes' : 'No')}}</td>
                <td>${{escapeHtml(trace.prompt_preview)}}</td>
                <td>${{escapeHtml(trace.response_preview)}}</td>
            </tr>
        `)
        .join('');
}}

async function fetchSnapshot() {{
    const commonParams = config.projectName ? {{ project_name: config.projectName }} : null;

    const [metricsRes, alertsRes, tracesRes] = await Promise.all([
        fetch(toUrl('/api/v1/analytics/realtime', commonParams), {{ headers: authHeaders() }}),
        fetch(toUrl('/api/v1/alerts', {{ ...(commonParams || {{}}), limit: config.alertLimit }}), {{ headers: authHeaders() }}),
        fetch(toUrl('/api/v1/traces/recent', {{ ...(commonParams || {{}}), limit: config.traceLimit }}), {{ headers: authHeaders() }}),
    ]);

    if (!metricsRes.ok || !alertsRes.ok || !tracesRes.ok) {{
        throw new Error('Failed to load initial snapshot');
    }}

    state.metrics = await metricsRes.json();
    state.alerts = await alertsRes.json();
    state.traces = await tracesRes.json();

    renderMetrics(state.metrics);
    renderAlerts(state.alerts);
    renderTraces(state.traces);
}}

function applyTraceEvent(payload) {{
    if (payload.metrics) {{
        state.metrics = payload.metrics;
        renderMetrics(state.metrics);
    }}

    if (payload.trace) {{
        state.traces = [payload.trace, ...state.traces].slice(0, config.traceLimit);
        renderTraces(state.traces);
    }}

    if (Array.isArray(payload.alerts) && payload.alerts.length > 0) {{
        state.alerts = [...payload.alerts, ...state.alerts].slice(0, config.alertLimit);
        renderAlerts(state.alerts);
    }}
}}

function parseSseFrame(frame) {{
    const lines = frame.split('\n');
    let eventName = 'message';
    const dataLines = [];

    for (const line of lines) {{
        if (line.startsWith('event:')) eventName = line.slice(6).trim();
        if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
    }}

    if (dataLines.length === 0) return;

    let payload;
    try {{
        payload = JSON.parse(dataLines.join('\n'));
    }} catch (_) {{
        return;
    }}

    if (eventName === 'trace_ingested' || payload.event_type === 'trace_ingested') {{
        applyTraceEvent(payload);
    }}
}}

async function connectSse() {{
    while (true) {{
        try {{
            updateStatus('Connecting SSE stream...');
            const streamUrl = toUrl(
                '/api/v1/events/stream',
                config.projectName ? {{ project_name: config.projectName }} : null,
            );

            const response = await fetch(streamUrl, {{
                method: 'GET',
                headers: authHeaders(),
            }});

            if (!response.ok || !response.body) {{
                throw new Error(`SSE connection failed with status ${{response.status}}`);
            }}

            updateStatus('Connected. Waiting for live trace events...');

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {{
                const {{ value, done }} = await reader.read();
                if (done) throw new Error('SSE stream closed');
                buffer += decoder.decode(value, {{ stream: true }});

                const frames = buffer.split('\n\n');
                buffer = frames.pop() || '';
                for (const frame of frames) parseSseFrame(frame);
            }}
        }} catch (error) {{
            updateStatus(`Disconnected. Reconnecting in 2s... (${{error.message}})`);
            await new Promise((resolve) => setTimeout(resolve, 2000));
        }}
    }}
}}

(async () => {{
    try {{
        updateStatus('Loading initial snapshot...');
        await fetchSnapshot();
        await connectSse();
    }} catch (error) {{
        updateStatus(`Failed to initialize stream: ${{error.message}}`);
    }}
}})();
</script>
""",
        height=980,
        scrolling=True,
)
