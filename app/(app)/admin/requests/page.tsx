"use client"

import * as React from "react"
import useSWR, { useSWRConfig } from "swr"
import { Check, X, Inbox } from "lucide-react"
import type { MusicRequest, RequestStatus } from "@/types/api"
import { api } from "@/lib/api"
import { useToast } from "@/components/providers/toast-provider"
import { PageHeader } from "@/components/page-header"
import { RequestCard } from "@/components/request-card"
import { EmptyState } from "@/components/empty-state"
import { CoverImage } from "@/components/cover-image"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { cn, formatRelativeDate } from "@/lib/utils"

type Filter = "pending" | "active" | "done" | "failed" | "all"

const FILTERS: { key: Filter; label: string; match: (s: RequestStatus) => boolean }[] = [
  { key: "pending", label: "Por aprobar", match: (s) => s === "PENDING" },
  { key: "active", label: "En curso", match: (s) => ["APPROVED", "SEARCHING", "DOWNLOADING"].includes(s) },
  { key: "done", label: "Listas", match: (s) => s === "AVAILABLE" },
  { key: "failed", label: "Fallidas", match: (s) => s === "FAILED" || s === "REJECTED" },
  { key: "all", label: "Todas", match: () => true },
]

export default function AdminRequestsPage() {
  const [filter, setFilter] = React.useState<Filter>("pending")
  const { data, isLoading } = useSWR<MusicRequest[]>("admin:requests", () => api.getAllRequests(), { refreshInterval: 4000 })
  const { mutate } = useSWRConfig()
  const { toast } = useToast()

  const requests = data ?? []
  const active = FILTERS.find((f) => f.key === filter)!
  const filtered = requests.filter((r) => active.match(r.status))

  const refresh = () => {
    mutate("admin:requests")
    mutate("admin:stats")
  }

  const moderate = async (req: MusicRequest, status: "APPROVED" | "REJECTED") => {
    try {
      await api.setRequestStatus(req.id, status)
      toast(status === "APPROVED" ? "Solicitud aprobada" : "Solicitud rechazada", status === "APPROVED" ? "success" : "info")
      refresh()
    } catch {
      toast("No se pudo actualizar", "error")
    }
  }

  return (
    <div>
      <PageHeader title="Moderar solicitudes" subtitle="Aprueba, rechaza y sigue las descargas de todos los usuarios." />

      <div className="mb-6 flex gap-2 overflow-x-auto no-scrollbar">
        {FILTERS.map((f) => {
          const count = requests.filter((r) => f.match(r.status)).length
          return (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                filter === f.key ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground",
              )}
            >
              {f.label}
              <span className={cn("rounded-full px-1.5 text-xs tabular-nums", filter === f.key ? "bg-primary-foreground/20" : "bg-background")}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={Inbox} title="Nada por aquí" description="No hay solicitudes en esta categoría." />
      ) : filter === "pending" ? (
        <div className="space-y-3">
          {filtered.map((req) => (
            <div key={req.id} className="flex items-center gap-3 rounded-2xl border border-border bg-card p-3">
              <CoverImage src={req.cover} alt={req.title} className="h-14 w-14" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{req.title}</p>
                <p className="truncate text-xs text-muted-foreground">{req.artist}</p>
                <div className="mt-1.5 flex items-center gap-2">
                  <StatusBadge status={req.status} />
                  <span className="text-xs text-muted-foreground">
                    {req.requestedByName} · {formatRelativeDate(req.createdAt)}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button size="icon-sm" variant="secondary" aria-label="Rechazar" onClick={() => moderate(req, "REJECTED")}>
                  <X className="h-4 w-4" />
                </Button>
                <Button size="icon-sm" aria-label="Aprobar" onClick={() => moderate(req, "APPROVED")}>
                  <Check className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {filtered.map((req) => (
            <RequestCard key={req.id} request={req} showRequester />
          ))}
        </div>
      )}
    </div>
  )
}
