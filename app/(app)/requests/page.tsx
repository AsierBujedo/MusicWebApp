"use client"

import * as React from "react"
import useSWR from "swr"
import { Inbox } from "lucide-react"
import type { MusicRequest, RequestStatus } from "@/types/api"
import { api } from "@/lib/api"
import { PageHeader } from "@/components/page-header"
import { RequestCard } from "@/components/request-card"
import { EmptyState } from "@/components/empty-state"
import { cn } from "@/lib/utils"

type Filter = "all" | "active" | "done" | "failed"

const ACTIVE: RequestStatus[] = ["PENDING", "APPROVED", "SEARCHING", "DOWNLOADING"]

export default function RequestsPage() {
  const [filter, setFilter] = React.useState<Filter>("all")
  const { data, isLoading } = useSWR<MusicRequest[]>("requests", () => api.getRequests(), {
    refreshInterval: 4000,
  })

  const requests = data ?? []
  const filtered = requests.filter((r) => {
    if (filter === "active") return ACTIVE.includes(r.status)
    if (filter === "done") return r.status === "AVAILABLE"
    if (filter === "failed") return r.status === "FAILED" || r.status === "REJECTED"
    return true
  })

  const counts = {
    all: requests.length,
    active: requests.filter((r) => ACTIVE.includes(r.status)).length,
    done: requests.filter((r) => r.status === "AVAILABLE").length,
    failed: requests.filter((r) => r.status === "FAILED" || r.status === "REJECTED").length,
  }

  const filters: { key: Filter; label: string }[] = [
    { key: "all", label: "Todas" },
    { key: "active", label: "En curso" },
    { key: "done", label: "Listas" },
    { key: "failed", label: "Fallidas" },
  ]

  return (
    <div>
      <PageHeader
        title="Solicitudes"
        subtitle="Sigue en tiempo real el estado de la música que has pedido."
      />

      <div className="mb-6 flex gap-2 overflow-x-auto no-scrollbar">
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
              filter === f.key ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground",
            )}
          >
            {f.label}
            <span
              className={cn(
                "rounded-full px-1.5 text-xs tabular-nums",
                filter === f.key ? "bg-primary-foreground/20" : "bg-background",
              )}
            >
              {counts[f.key]}
            </span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-2xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title={filter === "all" ? "Aún no has pedido música" : "Nada por aquí"}
          description={
            filter === "all"
              ? "Busca una canción y pulsa Solicitar. Aparecerá aquí mientras la conseguimos."
              : "No hay solicitudes en esta categoría."
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {filtered.map((req) => (
            <RequestCard key={req.id} request={req} />
          ))}
        </div>
      )}
    </div>
  )
}
