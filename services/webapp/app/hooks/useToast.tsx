import { useState, useCallback, useEffect } from "react";
import { createPortal } from "react-dom";
import { Toast, type ToastType } from "~/components/ui/Toast";

interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  // Only render portal after client-side mount to avoid hydration errors
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const showToast = useCallback((message: string, type: ToastType = "info", duration?: number) => {
    const id = Math.random().toString(36).substring(7);
    const newToast: ToastMessage = { id, message, type, duration };
    setToasts((prev) => [...prev, newToast]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const ToastContainer = useCallback(() => {
    // Don't render anything during SSR or before client mount
    if (!isMounted || typeof document === "undefined") return null;

    return createPortal(
      <div className="fixed top-4 right-4 z-50 pointer-events-none">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            duration={toast.duration}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>,
      document.body
    );
  }, [isMounted, toasts, removeToast]);

  return {
    showToast,
    ToastContainer,
  };
}