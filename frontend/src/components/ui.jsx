import { useEffect } from "react";

export function Badge({ value }) {
  if (!value) return null;
  return <span className={`badge badge-${value}`}>{String(value).replace(/_/g, " ")}</span>;
}

export function ProgressBar({ value }) {
  return (
    <div className="progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-fill" style={{ width: `${Math.min(value, 100)}%` }} />
      <span>{value}%</span>
    </div>
  );
}

/** Handles the loading / error / empty states for any data view. */
export function DataState({ loading, error, empty, emptyText, emptyHint, onRetry, children }) {
  if (loading) return <div className="state" aria-busy="true"><span className="spinner" />Loading…</div>;
  if (error) {
    return (
      <div className="state state-error" role="alert">
        <strong>Could not load data.</strong>
        <span>{error}</span>
        {onRetry && <button className="btn" onClick={onRetry}>Try again</button>}
      </div>
    );
  }
  if (empty) return <div className="state"><strong>{emptyText || "Nothing here yet."}</strong>{emptyHint && <span>{emptyHint}</span>}</div>;
  return children;
}

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const h = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "modal-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <header><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close">×</button></header>
        {children}
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
      <div className="page-actions">{children}</div>
    </div>
  );
}

export const fmtDate = (d) => (d ? new Date(d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "—");
export const isDemo = (s) => typeof s === "string" && s.startsWith("[DEMO]");
