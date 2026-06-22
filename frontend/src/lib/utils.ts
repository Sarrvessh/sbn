import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCost(cost: number | null | undefined): string {
  if (cost == null || isNaN(cost)) return "$0.000000";
  return `$${cost.toFixed(6)}`;
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms == null || isNaN(ms)) return "0.00 ms";
  return `${ms.toFixed(2)} ms`;
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function formatShortTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString();
}
