"use client"

import * as React from "react"
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react"
import { cn } from "@/lib/utils"

type ToastVariant = "success" | "error" | "info"
interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  toast: (message: string, variant?: ToastVariant) => void
}

const ToastContext = React.createContext<ToastContextValue | null>(null)

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
}

const ACCENT = {
  success: "text-status-available",
  error: "text-status-failed",
  info: "text-status-downloading",
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([])

  const toast = React.useCallback((message: string, variant: ToastVariant = "info") => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3800)
  }, [])

  const dismiss = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id))

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 z-[200] flex flex-col items-center gap-2 px-4"
        style={{ top: "calc(1rem + env(safe-area-inset-top, 0px))" }}
      >
        {toasts.map((t) => {
          const Icon = ICONS[t.variant]
          return (
            <div
              key={t.id}
              role="status"
              className="animate-in pointer-events-auto flex w-full max-w-sm items-center gap-3 rounded-2xl border border-border bg-popover px-4 py-3 shadow-xl"
            >
              <Icon className={cn("h-5 w-5 shrink-0", ACCENT[t.variant])} aria-hidden="true" />
              <p className="flex-1 text-sm text-popover-foreground">{t.message}</p>
              <button onClick={() => dismiss(t.id)} aria-label="Cerrar" className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = React.useContext(ToastContext)
  if (!ctx) throw new Error("useToast must be used within ToastProvider")
  return ctx
}
