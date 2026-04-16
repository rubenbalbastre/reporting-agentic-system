import { useEffect, useState } from "react";

export default function PromptModal({
  open,
  title,
  label = "Name",
  initialValue = "",
  confirmLabel = "Save",
  cancelLabel = "Cancel",
  loading = false,
  onConfirm,
  onCancel,
}) {
  const [value, setValue] = useState(initialValue || "");

  useEffect(() => {
    if (!open) return;
    setValue(initialValue || "");
  }, [open, initialValue]);

  if (!open) return null;

  const trimmed = value.trim();

  return (
    <div className="modal-backdrop confirm-backdrop" onClick={onCancel} role="presentation">
      <section
        className="confirm-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <h3>{title}</h3>
        <div className="prompt-field">
          <label>{label}</label>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && trimmed && !loading) onConfirm(trimmed);
            }}
            autoFocus
          />
        </div>
        <div className="confirm-actions">
          <button className="btn-ghost" onClick={onCancel} disabled={loading}>{cancelLabel}</button>
          <button className="btn-primary" onClick={() => onConfirm(trimmed)} disabled={loading || !trimmed}>
            {loading ? "Saving..." : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

