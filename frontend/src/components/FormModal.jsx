import { useState } from "react";
import { parseError } from "../api/client";
import { Modal } from "./ui";

/** fields: [{name,label,type:text|textarea|number|date|select,options:[{value,label}],required,hint}] */
export default function FormModal({ title, fields, initial = {}, submitLabel = "Save", onSubmit, onClose }) {
  const [values, setValues] = useState(() => Object.fromEntries(fields.map((f) => [f.name, initial[f.name] ?? (f.default ?? "")])));
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (n, v) => setValues((x) => ({ ...x, [n]: v }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setErrors({}); setFormError("");
    const payload = {};
    fields.forEach((f) => {
      let v = values[f.name];
      if (f.type === "number" || f.numeric) v = v === "" || v === null ? null : Number(v);
      payload[f.name] = v === "" && f.type !== "text" && f.type !== "textarea" ? null : v;
    });
    try {
      await onSubmit(payload);
      onClose();
    } catch (err) {
      const p = parseError(err);
      setErrors(p.fields || {});
      setFormError(p.message);
      setBusy(false);
    }
  }

  return (
    <Modal title={title} onClose={onClose}>
      <form onSubmit={submit} className="form" noValidate>
        {fields.map((f) => (
          <label key={f.name} className={`field ${errors[f.name] ? "has-error" : ""}`}>
            <span>{f.label}{f.required && " *"}</span>
            {f.type === "textarea" ? (
              <textarea rows={3} value={values[f.name] ?? ""} onChange={(e) => set(f.name, e.target.value)} />
            ) : f.type === "select" ? (
              <select value={values[f.name] ?? ""} onChange={(e) => set(f.name, e.target.value)}>
                {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : (
              <input type={f.type || "text"} min={f.type === "number" ? 0 : undefined}
                value={values[f.name] ?? ""} onChange={(e) => set(f.name, e.target.value)} required={f.required} />
            )}
            {f.hint && <small>{f.hint}</small>}
            {errors[f.name] && <em className="field-error">{f.label} {errors[f.name]}</em>}
          </label>
        ))}
        {formError && <div className="form-error" role="alert">{formError}</div>}
        <footer>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
        </footer>
      </form>
    </Modal>
  );
}
