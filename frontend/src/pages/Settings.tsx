import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchSettings, updateSettings } from "../lib/api";
import { useState } from "react";

const TABS = ["General", "Models", "Integrations", "SDK Config"];

export default function Settings() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("General");
  const [samplingRateDraft, setSamplingRateDraft] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => fetchSettings().catch(() => ({ default_agent_model: "", max_tokens: 1024, temperature: 0.2, sampling_rate: 100, budget_alert_threshold_pct: 80 })),
  });

  const samplingRate = samplingRateDraft ?? settings?.sampling_rate ?? 100;

  const updateMut = useMutation({
    mutationFn: (d: Record<string, unknown>) => updateSettings(d),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["settings"] }); setFeedback("Saved."); setTimeout(() => setFeedback(null), 2000); },
    onError: (err) => { setFeedback(`Error: ${err}`); setTimeout(() => setFeedback(null), 3000); },
  });

  const handleSave = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const payload: Record<string, unknown> = {};
    fd.forEach((v, k) => {
      if (k === "openai_api_key" && (v === "••••••••" || v === "")) return;
      payload[k] = v;
    });
    if (payload.sampling_rate !== undefined) payload.sampling_rate = Number(payload.sampling_rate);
    if (payload.max_tokens !== undefined) payload.max_tokens = Number(payload.max_tokens);
    if (payload.temperature !== undefined) payload.temperature = Number(payload.temperature);
    if (payload.budget_alert_threshold_pct !== undefined) payload.budget_alert_threshold_pct = Number(payload.budget_alert_threshold_pct);
    updateMut.mutate(payload);
  };

  if (isLoading) return <div className="page"><div style={{ fontSize: 13, color: "#6e6e73" }}>Loading settings…</div></div>;

  const sdkSnippet = `from sbn_sdk import SbnTracer

tracer = SbnTracer(
    api_key="<your-api-key>",
    base_url="http://localhost:8000",
    sampling_rate=${samplingRate},
)`;

  return (
    <div className="page">
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <h1 className="page-title">Settings</h1>
        {feedback && <span style={{ fontSize: 12, color: feedback.startsWith("Error") ? "#ff3b30" : "#34c759" }}>{feedback}</span>}
      </div>
      <p className="page-subtitle">Configure platform behavior and integrations</p>

      <div className="segmented">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={tab === t ? "active" : ""}>{t}</button>
        ))}
      </div>

      <form onSubmit={handleSave}>
        {tab === "General" && (
          <div className="flex flex-col gap-4">
            <div className="section-card">
              <div className="section-card-header">
                <div className="section-card-title">Platform Settings</div>
              </div>
              <div className="section-card-body">
                <div className="flex flex-col gap-3">
                  <div className="flex gap-4">
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Default Agent Model</label>
                      <input name="default_agent_model" defaultValue={settings?.default_agent_model ?? ""} className="input" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Max Tokens</label>
                      <input name="max_tokens" type="number" defaultValue={settings?.max_tokens ?? 1024} className="input" />
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Temperature</label>
                      <input name="temperature" type="number" step="0.1" defaultValue={settings?.temperature ?? 0.2} className="input" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>Budget Alert Threshold (%)</label>
                      <input name="budget_alert_threshold_pct" type="number" defaultValue={settings?.budget_alert_threshold_pct ?? 80} className="input" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="section-card">
              <div className="section-card-header">
                <div className="section-card-title">Sampling Rate</div>
              </div>
              <div className="section-card-body">
                <div className="flex items-center gap-4">
                  <input type="range" min="0" max="100" value={samplingRate} onChange={(e) => setSamplingRate(Number(e.target.value))} style={{ flex: 1, accentColor: "#0071e3" }} />
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 600, color: "#1d1d1f", minWidth: 48 }}>{samplingRate}%</span>
                </div>
                <input type="hidden" name="sampling_rate" value={samplingRate} />
              </div>
            </div>
          </div>
        )}

        {tab === "Models" && (
          <div className="section-card">
            <div className="section-card-header">
              <div className="section-card-title">Model Configuration</div>
            </div>
            <div className="section-card-body">
              <div className="flex flex-col gap-3">
                <div>
                  <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>OpenAI API Key</label>
                  <input name="openai_api_key" type="password" defaultValue={settings?.openai_api_key ? "••••••••" : ""} className="input" />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>OpenAI Base URL</label>
                  <input name="openai_base_url" defaultValue={settings?.openai_base_url || "https://openrouter.ai/api/v1"} className="input" />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>OpenAI Referer</label>
                  <input name="openai_referer" defaultValue={settings?.openai_referer || ""} className="input" />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "#6e6e73", display: "block", marginBottom: 4 }}>OpenAI App Title</label>
                  <input name="openai_app_title" defaultValue={settings?.openai_app_title || ""} className="input" />
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === "Integrations" && (
          <div className="flex gap-4">
            <div className="section-card" style={{ flex: 1 }}>
              <div className="section-card-header">
                <div className="section-card-title">Google ADK</div>
              </div>
              <div className="section-card-body">
                <p style={{ fontSize: 12, color: "#6e6e73", margin: "0 0 8px" }}>sbn_sdk integration for Google Agent Development Kit</p>
                <pre className="code-block" style={{ fontSize: 11 }}>{`from sbn_sdk.integrations.google_adk import instrument_runner
instrument_runner(tracer)`}</pre>
              </div>
            </div>
            <div className="section-card" style={{ flex: 1 }}>
              <div className="section-card-header">
                <div className="section-card-title">OCR Tracing</div>
              </div>
              <div className="section-card-body">
                <p style={{ fontSize: 12, color: "#6e6e73", margin: "0 0 8px" }}>Trace OCR (Optical Character Recognition) operations</p>
                <pre className="code-block" style={{ fontSize: 11 }}>{`from sbn_sdk.integrations.ocr import instrument_pytesseract
instrument_pytesseract(tracer)`}</pre>
              </div>
            </div>
          </div>
        )}

        {tab === "SDK Config" && (
          <div className="section-card">
            <div className="section-card-header">
              <div className="section-card-title">SDK Configuration</div>
            </div>
            <div className="section-card-body">
              <p style={{ fontSize: 12, color: "#6e6e73", margin: "0 0 8px" }}>Use this snippet to configure the SBN — ARMS SDK in your application.</p>
              <pre className="code-block dark" style={{ fontSize: 12 }}>{sdkSnippet}</pre>
            </div>
          </div>
        )}

        <div style={{ marginTop: 20 }}>
          <button type="submit" className="btn btn-primary" disabled={updateMut.isPending}>{updateMut.isPending ? "Saving…" : "Save Settings"}</button>
        </div>
      </form>
    </div>
  );
}
