"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

let toastListeners: ((toasts: Toast[]) => void)[] = [];
let toasts: Toast[] = [];

const toast = {
  success: (message: string) => addToast(message, "success"),
  error: (message: string) => addToast(message, "error"),
  info: (message: string) => addToast(message, "info"),
  warning: (message: string) => addToast(message, "warning"),
};

function addToast(message: string, type: ToastType) {
  const id = Math.random().toString(36).substring(7);
  const newToast: Toast = { id, message, type };
  toasts = [...toasts, newToast];
  toastListeners.forEach((listener) => listener(toasts));

  setTimeout(() => {
    removeToast(id);
  }, 5000);
}

function removeToast(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  toastListeners.forEach((listener) => listener(toasts));
}

export function useToast() {
  const [currentToasts, setCurrentToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (newToasts: Toast[]) => {
      setCurrentToasts(newToasts);
    };
    toastListeners.push(listener);
    setCurrentToasts([...toasts]);

    return () => {
      toastListeners = toastListeners.filter((l) => l !== listener);
    };
  }, []);

  return { toasts: currentToasts };
}

export function Toaster() {
  const { toasts: currentToasts } = useToast();

  if (currentToasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {currentToasts.map((toast) => (
        <Alert
          key={toast.id}
          className={cn(
            "shadow-lg animate-in slide-in-from-right",
            toast.type === "success" && "border-green-500/50 bg-green-500/10",
            toast.type === "error" && "border-red-500/50 bg-red-500/10",
            toast.type === "info" && "border-blue-500/50 bg-blue-500/10",
            toast.type === "warning" && "border-amber-500/50 bg-amber-500/10"
          )}
        >
          <div className="flex items-start gap-2">
            {toast.type === "success" && (
              <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
            )}
            {toast.type === "error" && (
              <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
            )}
            {toast.type === "info" && (
              <Info className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
            )}
            {toast.type === "warning" && (
              <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
            )}
            <AlertDescription className="flex-1 text-sm">
              {toast.message}
            </AlertDescription>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-muted-foreground hover:text-foreground shrink-0"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </Alert>
      ))}
    </div>
  );
}

export { toast };
