import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

/**
 * Modal — components-web/modal.md
 * Focused, interruptive tasks. Backdrop: color.mask.base.
 * Entrance: opacity 0 + scale(0.96) → 1 + scale(1), 150–200ms ease-out.
 * Exit ≈ 75% of enter duration. Only one interruptive overlay at a time.
 */

export type ModalSize = "small" | "medium" | "large";

interface ModalProps {
  open: boolean;
  size?: ModalSize;
  title: string;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  onClose?: () => void;
  closeOnBackdrop?: boolean;
}

export default function Modal({
  open,
  size = "medium",
  title,
  description,
  children,
  footer,
  onClose,
  closeOnBackdrop = true,
}: ModalProps) {
  const [exiting, setExiting] = useState(false);
  const [render, setRender] = useState(open);
  const frameRef = useRef<HTMLDivElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useRef(`modal-title-${Math.random().toString(36).slice(2, 9)}`);

  const requestClose = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    // Exit duration ~75% of the 190ms entrance
    setTimeout(() => {
      setExiting(false);
      setRender(false);
      onClose?.();
    }, 140);
  }, [exiting, onClose]);

  useEffect(() => {
    if (open) {
      restoreFocusRef.current = document.activeElement as HTMLElement | null;
      setRender(true);
      setExiting(false);
    }
  }, [open]);

  useEffect(() => {
    if (!render) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") requestClose();
    };
    document.addEventListener("keydown", onKey);
    // Focus the first focusable element inside the frame
    const frame = frameRef.current;
    const focusables = frame?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    (focusables && focusables.length > 0 ? focusables[0] : frame)?.focus();
    // Trap focus
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !frame) return;
      const items = Array.from(
        frame.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => !el.hasAttribute("disabled"));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trap);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("keydown", trap);
      document.body.style.overflow = prevOverflow;
      restoreFocusRef.current?.focus?.();
    };
  }, [render, requestClose]);

  if (!render) return null;

  return createPortal(
    <div
      className={`overlay-backdrop modal ${exiting ? "exiting" : ""}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && closeOnBackdrop) requestClose();
      }}
    >
      <div
        ref={frameRef}
        className={`modal-frame ${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId.current}
        tabIndex={-1}
      >
        <div className="modal-title-row">
          <div className="modal-title" id={titleId.current}>{title}</div>
          <button className="icon-btn" onClick={requestClose} aria-label="Close" style={{ width: 24, height: 24 }}>
            <X size={16} />
          </button>
        </div>
        {description && <p className="modal-description">{description}</p>}
        {children && <div className="modal-body">{children}</div>}
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body
  );
}
