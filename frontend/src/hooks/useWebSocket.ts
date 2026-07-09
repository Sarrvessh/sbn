import { useEffect, useRef, useCallback } from "react";
import { getApiKey } from "../lib/api";
import { useSSE } from "./useSSE";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

interface WebSocketOptions {
  projectName?: string;
  onMetrics?: (metrics: unknown) => void;
  onTrace?: (trace: unknown) => void;
  onAlerts?: (alerts: unknown[]) => void;
}

function getWsUrl(base: string, projectName?: string): string {
  const wsBase = base.replace(/^http/, "ws");
  const apiKey = getApiKey();
  const params = new URLSearchParams();
  if (projectName) params.set("project_name", projectName);
  if (apiKey) params.set("api_key", apiKey);
  const qs = params.toString();
  return `${wsBase}/api/v1/events/ws${qs ? "?" + qs : ""}`;
}

export function useWebSocket({
  projectName,
  onMetrics,
  onTrace,
  onAlerts,
}: WebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const abortedRef = useRef(false);
  const wsSupported = typeof WebSocket !== "undefined";

  const onMetricsRef = useRef(onMetrics);
  const onTraceRef = useRef(onTrace);
  const onAlertsRef = useRef(onAlerts);
  onMetricsRef.current = onMetrics;
  onTraceRef.current = onTrace;
  onAlertsRef.current = onAlerts;

  const connect = useCallback(() => {
    if (!wsSupported) return;
    const apiKey = getApiKey();
    if (!apiKey) return;

    try {
      const url = getWsUrl(BACKEND_URL, projectName);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {};

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event_type === "trace_ingested") {
            if (data.metrics) onMetricsRef.current?.(data.metrics);
            if (data.trace) onTraceRef.current?.(data.trace);
            if (data.alerts?.length) onAlertsRef.current?.(data.alerts);
          }
        } catch {}
      };

      ws.onclose = () => {
        if (!abortedRef.current) {
          reconnectTimer.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimer.current = setTimeout(connect, 3000);
    }
  }, [projectName, wsSupported]);

  useEffect(() => {
    abortedRef.current = false;
    connect();
    return () => {
      abortedRef.current = true;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { supported: wsSupported };
}

export function useRealtimeEvents(opts: WebSocketOptions) {
  const ws = useWebSocket(opts);
  useSSE({ ...opts, enabled: !ws.supported });
}
