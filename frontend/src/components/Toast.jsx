import { createContext, useCallback, useContext, useState } from "react";

const ToastCtx = createContext(null);
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((kind, text) => {
    const id = Math.random();
    setItems((x) => [...x, { id, kind, text }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), kind === "error" ? 7000 : 3500);
  }, []);
  const api = { success: (t) => push("success", t), error: (t) => push("error", t) };
  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((i) => <div key={i.id} className={`toast toast-${i.kind}`}>{i.text}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}
