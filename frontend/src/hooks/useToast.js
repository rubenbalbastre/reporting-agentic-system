import { useCallback, useMemo, useState } from "react";

export function useToast() {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback((type, text) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { id, type, text }]);
    window.setTimeout(() => removeToast(id), 2800);
  }, [removeToast]);

  const api = useMemo(
    () => ({
      success: (text) => pushToast("success", text),
      error: (text) => pushToast("error", text),
      info: (text) => pushToast("info", text),
      remove: removeToast,
    }),
    [pushToast, removeToast],
  );

  return { toasts, toast: api };
}
