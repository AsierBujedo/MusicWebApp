"use client"

import useSWR from "swr"
import Link from "next/link"
import { Users, Inbox, Download, Music, ChevronRight, Radio } from "lucide-react"
import type { AdminStats, MusicRequest, ServiceHealth } from "@/types/api"
import { api } from "@/lib/api"
import { PageHeader } from "@/components/page-header"
import { RequestCard } from "@/components/request-card"
import { cn } from "@/lib/utils"

const STATUS_DOT: Record<ServiceHealth["status"], string> = {
  online: "bg-status-available",
  degraded: "bg-status-pending",
  offline: "bg-status-failed",
}

export default function AdminDashboardPage() {
  const { data: stats, isLoading } = useSWR<AdminStats>("admin:stats", () => api.getStats(), { refreshInterval: 5000 })
  const { data: requests } = useSWR<MusicRequest[]>("admin:requests", () => api.getAllRequests(), { refreshInterval: 4000 })
  const { data: services } = useSWR<ServiceHealth[]>("admin:services", () => api.getServices(), { refreshInterval: 8000 })

  const cards = [
    { icon: Users, label: "Usuarios", value: stats?.users, href: "/admin/users" },
    { icon: Inbox, label: "Solicitudes", value: stats?.requests, href: "/admin/requests" },
    { icon: Download, label: "Descargando", value: stats?.downloads, href: "/admin/requests" },
    { icon: Music, label: "Canciones", value: stats?.availableTracks, href: "/admin/tracks" },
  ]

  const activeRequests = (requests ?? []).filter((r) =>
    ["PENDING", "APPROVED", "SEARCHING", "DOWNLOADING"].includes(r.status),
  )

  return (
    <div>
      <PageHeader title="Panel de administración" subtitle="Visión general del sistema en tiempo real." />

      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((c) => {
          const Icon = c.icon
          const content = (
            <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-5 transition-colors hover:border-primary/40">
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/12 text-primary">
                  <Icon className="h-5 w-5" />
                </span>
                {c.href && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
              </div>
              <div>
                <p className="text-3xl font-semibold tabular-nums">
                  {isLoading || c.value === undefined ? <span className="skeleton inline-block h-8 w-10 rounded" /> : c.value}
                </p>
                <p className="text-sm text-muted-foreground">{c.label}</p>
              </div>
            </div>
          )
          return c.href ? (
            <Link key={c.label} href={c.href}>
              {content}
            </Link>
          ) : (
            <div key={c.label}>{content}</div>
          )
        })}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Solicitudes activas</h2>
            <Link href="/admin/requests" className="flex items-center text-sm text-muted-foreground hover:text-foreground">
              Ver todas <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
          {activeRequests.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              No hay descargas en curso ahora mismo.
            </div>
          ) : (
            <div className="space-y-3">
              {activeRequests.slice(0, 5).map((req) => (
                <RequestCard key={req.id} request={req} showRequester />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center gap-2">
            <Radio className="h-4 w-4 text-muted-foreground" />
            <h2 className="font-display text-lg font-semibold">Servicios</h2>
          </div>
          <div className="space-y-2 rounded-2xl border border-border bg-card p-2">
            {(services ?? []).map((s) => (
              <div key={s.key} className="flex items-center gap-3 rounded-xl px-3 py-2.5">
                <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", STATUS_DOT[s.status])} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{s.name}</p>
                  {s.detail && <p className="truncate text-xs text-muted-foreground">{s.detail}</p>}
                </div>
                <span className="text-xs capitalize text-muted-foreground">{s.status}</span>
              </div>
            ))}
            {!services && (
              <div className="space-y-2 p-1">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="skeleton h-12 rounded-xl" />
                ))}
              </div>
            )}
          </div>
          <Link
            href="/admin/services"
            className="mt-2 flex items-center justify-center rounded-xl border border-border py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Gestionar servicios
          </Link>
        </section>
      </div>
    </div>
  )
}
