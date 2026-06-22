import { useEffect, useRef, useCallback } from "react";
import { getApiKey } from "../lib/api";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

interface SSEOptions {
  projectName?: string;
  onMetrics?: (metrics: unknown) => void;
  onTrace?: (trace: unknown) => void;
  onAlerts?: (alerts: unknown[]) => void;
}

export function useSSE({
  projectName,
  onMetrics,
  onTrace,
  onAlerts,
}: SSEOptions) {
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const abortedRef = useRef(false);

  const connect = useCallback(() => {
    const apiKey = getApiKey();
    if (!apiKey) return;

    const params = projectName
      ? `?project_name=${encodeURIComponent(projectName)}`
      : "";
    const url = `${BACKEND_URL}/api/v1/events/stream${params}`;

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

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() || "";
          for (const frame of frames) {
            const event = parseSSEFrame(frame);
            if (event) {
              if (event.event_type === "trace_ingested") {
                if (event.metrics) onMetrics?.(event.metrics);
                if (event.trace) onTrace?.(event.trace);
                if (event.alerts?.length) onAlerts?.(event.alerts);
              }
            }
          }
        }
        scheduleReconnect(connect, abortedRef, reconnectTimer);
      })
      .catch(() => {
        scheduleReconnect(connect, abortedRef, reconnectTimer);
      });

    return () => {
      abortedRef.current = true;
      abortController.abort();
      readerRef.current?.cancel();
    };
  }, [projectName, onMetrics, onTrace, onAlerts]);

  useEffect(() => {
    abortedRef.current = false;
    const cleanup = connect();
    return () => {
      cleanup?.();
      clearTimeout(reconnectTimer.current);
    };
  }, [connect]);
}

function scheduleReconnect(
  connect: () => (() => void) | undefined,
  abortedRef: React.MutableRefObject<boolean>,
  reconnectTimer: React.MutableRefObject<ReturnType<typeof setTimeout> | undefined>,
) {
  if (abortedRef.current) return;
  reconnectTimer.current = setTimeout(connect, 3000);
}

function parseSSEFrame(frame: string) {
  const lines = frame.split("\n");
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }

  if (!dataLines.length) return null;

  try {
    return JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }
}
