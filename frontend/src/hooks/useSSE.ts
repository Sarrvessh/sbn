import { useEffect, useRef, useCallback } from "react";
import { getApiKey } from "../lib/api";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

interface SSEOptions {
  projectName?: string;
  onMetrics?: (metrics: unknown) => void;
  onTrace?: (trace: unknown) => void;
  onAlerts?: (alerts: unknown[]) => void;
  enabled?: boolean;
}

export function useSSE({
  projectName,
  onMetrics,
  onTrace,
  onAlerts,
  enabled = true,
}: SSEOptions) {
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const abortedRef = useRef(false);
  const lastEventIdRef = useRef<string | null>(null);
  const connectRef = useRef<() => (() => void) | undefined>();

  const onMetricsRef = useRef(onMetrics);
  const onTraceRef = useRef(onTrace);
  const onAlertsRef = useRef(onAlerts);
  onMetricsRef.current = onMetrics;
  onTraceRef.current = onTrace;
  onAlertsRef.current = onAlerts;

  const connect = useCallback(() => {
    if (!enabled) return;
    const apiKey = getApiKey();
    if (!apiKey) return;

    const params = new URLSearchParams();
    if (projectName) params.set("project_name", projectName);
    if (lastEventIdRef.current) params.set("last_event_id", lastEventIdRef.current);
    const url = `${BACKEND_URL}/api/v1/events/stream${
      params.toString() ? "?" + params.toString() : ""
    }`;

    const abortController = new AbortController();

    fetch(url, {
      headers: { "X-API-Key": apiKey },
      signal: abortController.signal,
    })
      .then(async (res) => {
        if (!res.ok || !res.body) throw new Error("SSE connection failed");
        const reader = res.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const frames = buffer.split("\n\n");
            buffer = frames.pop() || "";
            for (const frame of frames) {
              const { eventId, data } = parseSSEFrame(frame);
              if (!data) continue;
              if (eventId) lastEventIdRef.current = eventId;
              if (data.event_type === "trace_ingested") {
                if (data.metrics) onMetricsRef.current?.(data.metrics);
                if (data.trace) onTraceRef.current?.(data.trace);
                if (data.alerts?.length) onAlertsRef.current?.(data.alerts);
              }
            }
          }
        } catch {
          // reader error
        }
        scheduleReconnect(connectRef, abortedRef, reconnectTimer);
      })
      .catch(() => {
        scheduleReconnect(connectRef, abortedRef, reconnectTimer);
      });

    return () => {
      abortedRef.current = true;
      abortController.abort();
      readerRef.current?.cancel();
    };
  }, [projectName, enabled]);

  connectRef.current = connect;

  useEffect(() => {
    abortedRef.current = false;
    const cleanup = connect();
    return () => {
      cleanup?.();
      clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return null;
}

function scheduleReconnect(
  connectRef: React.MutableRefObject<(() => (() => void) | undefined) | undefined>,
  abortedRef: React.MutableRefObject<boolean>,
  reconnectTimer: React.MutableRefObject<ReturnType<typeof setTimeout> | undefined>,
) {
  if (abortedRef.current) return;
  reconnectTimer.current = setTimeout(() => connectRef.current?.(), 3000);
}

function parseSSEFrame(frame: string): { eventId: string | null; data: unknown } {
  const lines = frame.split("\n");
  const dataLines: string[] = [];
  let eventId: string | null = null;

  for (const line of lines) {
    if (line.startsWith("id:")) eventId = line.slice(3).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }

  if (!dataLines.length) return { eventId: null, data: null };

  try {
    return { eventId, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return { eventId: null, data: null };
  }
}
