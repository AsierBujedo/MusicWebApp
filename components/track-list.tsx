"use client"

import type { Track } from "@/types/api"
import { TrackItem, TrackItemSkeleton } from "@/components/track-item"

export function TrackList({
  tracks,
  onRemove,
}: {
  tracks: Track[]
  onRemove?: (track: Track) => void
}) {
  return (
    <div className="space-y-0.5">
      {tracks.map((track, i) => (
        <TrackItem key={track.id} track={track} queue={tracks} index={i} onRemove={onRemove} />
      ))}
    </div>
  )
}

export function TrackListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="space-y-0.5">
      {Array.from({ length: count }).map((_, i) => (
        <TrackItemSkeleton key={i} />
      ))}
    </div>
  )
}

// A horizontal scroller for cards on wider content.
export function Section({
  title,
  subtitle,
  children,
  action,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div><h2 className="font-display text-lg font-semibold tracking-tight">{title}</h2>{subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}</div>
        {action}
      </div>
      {children}
    </section>
  )
}
