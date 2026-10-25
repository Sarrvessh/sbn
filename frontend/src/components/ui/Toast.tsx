import { createContext, useCallback, useContext, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from "lucide-react";

/**
 * Toast — components-web/toast.md
 * Non-blocking transient feedback, fixed top-center, auto-dismiss 3s.
 * Types: success | error | info | loading | caution.
 * Background is constant (color.mask.toastPc); only the icon color changes.
 */

export type ToastType = "success" | "error" | "info" | "loading" | "caution";

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
  exiting?: boolean;
}

interface ToastContextValue {
  toast: (type: ToastType, message: string) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  caution: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

const MAX_STACK = 3;
const DISMISS_MS = 3000;
const EXIT_MS = 260;

const TYPE_ICON: Record<Exclude<ToastType, "info">, { Icon: typeof CheckCircle2; color: string }> = {
  success: { Icon: CheckCircle2, color: "var(--green)" },
  error: { Icon: XCircle, color: "var(--red)" },
  caution: { Icon: AlertTriangle, color: "var(--orange)" },
  loading: { Icon: Loader2, color: "rgba(255,255,255,0.6)" },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const idRef = useRef(0);
  const timersRef = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), EXIT_MS);
  }, []);

  const push = useCallback(
    (type: ToastType, message: string) => {
      const id = ++idRef.current;
      setToasts((prev) => {
        const next = [{ id, type, message }, ...prev];
        // Max stack 3 — dismiss oldest
        if (next.length > MAX_STACK) {
          const dropped = next[next.length - 1];
          const timer = timersRef.current.get(dropped.id);
          if (timer) clearTimeout(timer);
          return next.slice(0, MAX_STACK);
        }
        return next;
      });
      if (type !== "loading") {
        const timer = setTimeout(() => remove(id), DISMISS_MS);
        timersRef.current.set(id, timer);
      }
    },
    [remove]
  );

  const pause = useCallback((id: number) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const resume = useCallback(
    (id: number) => {
      if (!timersRef.current.has(id)) {
        timersRef.current.set(id, setTimeout(() => remove(id), 1200));
      }
    },
    [remove]
  );

  const value: ToastContextValue = {
    toast: push,
    success: (m) => push("success", m),
    error: (m) => push("error", m),
    info: (m) => push("info", m),
    caution: (m) => push("caution", m),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div className="toast-stack">
          {toasts.map((t) => {
            const meta = t.type === "info" ? null : TYPE_ICON[t.type as Exclude<ToastType, "info">];
            return (
              <div
                key={t.id}
                className={`toast ${t.exiting ? "exiting" : ""}`}
                role={t.type === "error" ? "alert" : "status"}
                aria-live={t.type === "error" ? "assertive" : "polite"}
                onMouseEnter={() => pause(t.id)}
                onMouseLeave={() => resume(t.id)}
              >
                {meta && (
                  <span className="toast-icon" style={{ color: meta.color }}>
                    <meta.Icon size={20} className={t.type === "loading" ? "spin" : undefined} />
                  </span>
                )}
                <span className="toast-message">{t.message}</span>
              </div>
            );
          })}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}
