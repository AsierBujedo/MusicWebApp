"use client"

import { Play, Pause, Download, Heart, MoreHorizontal, ListPlus, Loader2, Trash2 } from "lucide-react"
import type { Track } from "@/types/api"
import { cn, formatDuration } from "@/lib/utils"
import { usePlayer } from "@/components/providers/player-provider"
import { useLibrary } from "@/components/providers/library-provider"
import { StatusBadge } from "@/components/status-badge"
import { CoverImage } from "@/components/cover-image"
import { Button } from "@/components/ui/button"
import { Dropdown, DropdownItem } from "@/components/ui/dropdown"

export function TrackItem({
  track,
  queue,
  onRemove,
  index,
}: {
  track: Track
  queue?: Track[]
  onRemove?: (track: Track) => void
  index?: number
}) {
  const { play, currentTrack, isPlaying, togglePlay } = usePlayer()
  const { isFavorite, toggleFavorite, requestTrack, addToPlaylist } = useLibrary()

  const isCurrent = currentTrack?.id === track.id
  const fav = isFavorite(track.id)
  const available = track.status === "AVAILABLE"

  const handlePrimary = () => {
    if (!available) return
    if (isCurrent) togglePlay()
    else play(track, queue)
  }

  return (
    <div
      className={cn(
        "group flex items-center gap-3 rounded-2xl px-2 py-2 transition-colors sm:px-3",
        isCurrent ? "bg-secondary" : "hover:bg-secondary/60",
      )}
    >
      <div className="relative">
        <CoverImage src={track.cover} alt={`${track.title} — ${track.artist}`} className="h-12 w-12 sm:h-14 sm:w-14" />
        {available && (
          <button
            onClick={handlePrimary}
            aria-label={isCurrent && isPlaying ? "Pausar" : "Reproducir"}
            className="absolute inset-0 flex items-center justify-center rounded-lg bg-black/45 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 aria-[current]:opacity-100"
            aria-current={isCurrent ? "true" : undefined}
          >
            {isCurrent && isPlaying ? (
              <Pause className="h-5 w-5 text-white" />
            ) : (
              <Play className="h-5 w-5 fill-white text-white" />
            )}
          </button>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className={cn("truncate text-sm font-medium", isCurrent && "text-primary")}>{track.title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {track.artist}
          {track.album ? ` · ${track.album}` : ""}
        </p>
        <div className="mt-1">
          <StatusBadge status={track.status} progress={track.progress} />
        </div>
      </div>

      <div className="flex items-center gap-1">
        {available ? (
          <span className="hidden w-12 text-right text-xs tabular-nums text-muted-foreground sm:block">
            {formatDuration(track.duration)}
          </span>
        ) : track.status === "DOWNLOADING" ? (
          <span className="hidden items-center gap-1 text-xs text-status-downloading sm:flex">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          </span>
        ) : (track.requestable || track.status === "REQUESTABLE" || track.status === "UNAVAILABLE") ? (
          <Button size="sm" variant="secondary" onClick={() => requestTrack(track)} className="gap-1.5">
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Solicitar</span>
          </Button>
        ) : null}

        <Dropdown
          trigger={
            <Button variant="ghost" size="icon-sm" aria-label="Más opciones">
              <MoreHorizontal className="h-5 w-5" />
            </Button>
          }
        >
          <DropdownItem icon={Heart} onClick={() => toggleFavorite(track)}>
            {fav ? "Quitar de favoritos" : "Añadir a favoritos"}
          </DropdownItem>
          <DropdownItem icon={ListPlus} onClick={() => addToPlaylist(track)}>
            Añadir a playlist
          </DropdownItem>
          {!available && track.status !== "DOWNLOADING" && (
            <DropdownItem icon={Download} onClick={() => requestTrack(track)}>
              Solicitar
            </DropdownItem>
          )}
          {onRemove && (
            <DropdownItem icon={Trash2} destructive onClick={() => onRemove(track)}>
              Quitar
            </DropdownItem>
          )}
        </Dropdown>

        <button
          onClick={() => toggleFavorite(track)}
          aria-label={fav ? "Quitar de favoritos" : "Añadir a favoritos"}
          aria-pressed={fav}
          className={cn(
            "hidden h-8 w-8 items-center justify-center rounded-full transition-colors sm:flex",
            fav ? "text-primary" : "text-muted-foreground hover:text-foreground",
          )}
        >
          <Heart className={cn("h-4 w-4", fav && "fill-current")} />
        </button>
      </div>
    </div>
  )
}

export function TrackItemSkeleton() {
  return (
    <div className="flex items-center gap-3 px-2 py-2 sm:px-3">
      <div className="skeleton h-12 w-12 rounded-lg sm:h-14 sm:w-14" />
      <div className="flex-1 space-y-2">
        <div className="skeleton h-3.5 w-1/3 rounded" />
        <div className="skeleton h-3 w-1/4 rounded" />
      </div>
      <div className="skeleton h-8 w-20 rounded-full" />
    </div>
  )
}
