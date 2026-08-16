"use client"

import useSWR from "swr"
import { Clock } from "lucide-react"
import type { HistoryEntry } from "@/types/api"
import { api } from "@/lib/api"
import { PageHeader } from "@/components/page-header"
import { TrackItem, TrackItemSkeleton } from "@/components/track-item"
import { EmptyState } from "@/components/empty-state"
import { formatRelativeDate } from "@/lib/utils"

function groupByDay(entries: HistoryEntry[]) {
  const groups = new Map<string, HistoryEntry[]>()
  const now = new Date()
  for (const entry of entries) {
    const d = new Date(entry.playedAt)
    const sameDay = d.toDateString() === now.toDateString()
    const yesterday = new Date(now)
    yesterday.setDate(now.getDate() - 1)
    const isYesterday = d.toDateString() === yesterday.toDateString()
    const label = sameDay ? "Hoy" : isYesterday ? "Ayer" : d.toLocaleDateString("es-ES", { day: "numeric", month: "long" })
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label)!.push(entry)
  }
  return [...groups.entries()]
}

export default function HistoryPage() {
  const { data, isLoading } = useSWR<HistoryEntry[]>("history", () => api.getHistory())
  const entries = data ?? []
  const grouped = groupByDay(entries)

  return (
    <div>
      <PageHeader title="Historial" subtitle="Todo lo que has escuchado, de lo más reciente a lo más antiguo." />

      {isLoading ? (
        <div className="space-y-1">
          {Array.from({ length: 6 }).map((_, i) => (
            <TrackItemSkeleton key={i} />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <EmptyState icon={Clock} title="Historial vacío" description="Las canciones que reproduzcas aparecerán aquí." />
      ) : (
        <div className="space-y-6">
          {grouped.map(([label, items]) => (
            <section key={label}>
              <h2 className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</h2>
              <div className="space-y-0.5">
                {items.map((entry, i) => (
                  <div key={`${entry.track.id}-${i}`} className="flex items-center gap-2">
                    <div className="min-w-0 flex-1">
                      <TrackItem track={entry.track} queue={items.map((e) => e.track)} index={i} />
                    </div>
                    <span className="hidden w-16 shrink-0 text-right text-xs text-muted-foreground sm:block">
                      {formatRelativeDate(entry.playedAt)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
