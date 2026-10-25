import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";

/**
 * Dialog — components-web/dialog.md
 * Pure-text binary confirmation. Fixed 360px. No close button.
 * role="alertdialog"; backdrop click triggers the safe (secondary) action.
 * Destructive dialogs focus the cancel action first.
 */

interface DialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function Dialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  loading = false,
  onConfirm,
  onCancel,
}: DialogProps) {
  const [exiting, setExiting] = useState(false);
  const [render, setRender] = useState(open);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const titleId = useRef(`dialog-title-${Math.random().toString(36).slice(2, 9)}`);
  const descId = useRef(`dialog-desc-${Math.random().toString(36).slice(2, 9)}`);
  const pendingAction = useRef<(() => void) | null>(null);

  const dismiss = useCallback((after?: () => void) => {
    if (exiting) return;
    pendingAction.current = after ?? null;
    setExiting(true);
    setTimeout(() => {
      setExiting(false);
      setRender(false);
      pendingAction.current?.();
    }, 140);
  }, [exiting]);

  useEffect(() => {
    if (open) {
      setRender(true);
      setExiting(false);
    }
  }, [open]);

  useEffect(() => {
    if (!render) return;
    // Destructive: focus cancel first; otherwise focus confirm.
    (danger ? cancelRef : confirmRef).current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss(onCancel);
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [render, danger, dismiss, onCancel]);

  if (!render) return null;

  return createPortal(
    <div
      className={`overlay-backdrop dialog ${exiting ? "exiting" : ""}`}
      onMouseDown={(e) => {
        // Backdrop click = safe action
        if (e.target === e.currentTarget) dismiss(onCancel);
      }}
    >
      <div
        className="dialog-frame"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId.current}
        aria-describedby={descId.current}
      >
        <div className="dialog-title" id={titleId.current}>{title}</div>
        <div className="dialog-description" id={descId.current}>{description}</div>
        <div className="dialog-footer">
          <button ref={cancelRef} className="btn btn-secondary" onClick={() => dismiss(onCancel)} disabled={loading}>
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            className={`btn ${danger ? "btn-danger" : "btn-primary"}`}
            onClick={() => dismiss(onConfirm)}
            disabled={loading}
          >
            {loading ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
