import type { RequestStatus, TrackStatus } from "@/types/api"
import { cn } from "@/lib/utils"

type AnyStatus = TrackStatus | RequestStatus

const CONFIG: Record<AnyStatus, { label: string; color: string; text: string }> = {
  AVAILABLE: { label: "Disponible", color: "bg-status-available", text: "text-status-available" },
  REQUESTABLE: { label: "No disponible", color: "bg-status-requestable", text: "text-status-requestable" },
  UNAVAILABLE: { label: "No disponible", color: "bg-status-requestable", text: "text-status-requestable" },
  PENDING: { label: "Pendiente", color: "bg-status-pending", text: "text-status-pending" },
  APPROVED: { label: "Aprobada", color: "bg-status-available", text: "text-status-available" },
  SEARCHING: { label: "Buscando una fuente…", color: "bg-status-downloading", text: "text-status-downloading" },
  DOWNLOADING: { label: "Descargando", color: "bg-status-downloading", text: "text-status-downloading" },
  FAILED: { label: "No se pudo descargar", color: "bg-status-failed", text: "text-status-failed" },
  REJECTED: { label: "Rechazada", color: "bg-status-failed", text: "text-status-failed" },
}

export function StatusBadge({
  status,
  progress,
  className,
}: {
  status: AnyStatus
  progress?: number
  className?: string
}) {
  const cfg = CONFIG[status]
  const showProgress = status === "DOWNLOADING" && typeof progress === "number"
  const pulse = status === "SEARCHING" || status === "DOWNLOADING" || status === "PENDING"

  return (
    <span className={cn("inline-flex items-center gap-2 text-xs font-medium", cfg.text, className)}>
      <span className="relative flex h-2 w-2">
        {pulse && <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", cfg.color)} />}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", cfg.color)} />
      </span>
      {showProgress ? `${cfg.label} ${progress}%` : cfg.label}
    </span>
  )
}
