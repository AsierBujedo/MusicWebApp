"use client"

import { RotateCw, Trash2, Play } from "lucide-react"
import type { MusicRequest } from "@/types/api"
import { api } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { useToast } from "@/components/providers/toast-provider"
import { CoverImage } from "@/components/cover-image"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { formatRelativeDate } from "@/lib/utils"
import { useSWRConfig } from "swr"

export function RequestCard({ request, showRequester }: { request: MusicRequest; showRequester?: boolean }) {
  const { play } = usePlayer()
  const { toast } = useToast()
  const { mutate } = useSWRConfig()

  const isDownloading = request.status === "DOWNLOADING"
  const isDone = request.status === "AVAILABLE"
  const isFailed = request.status === "FAILED" || request.status === "REJECTED"

  const refresh = () => {
    mutate("requests")
    mutate("admin:requests")
  }

  const handleRetry = async () => {
    try {
      await api.retryRequest(request.id)
      toast("Reintentando la solicitud", "info")
      refresh()
    } catch {
      toast("No se pudo reintentar", "error")
    }
  }

  const handleDelete = async () => {
    try {
      await api.deleteRequest(request.id)
      toast("Solicitud eliminada", "info")
      refresh()
    } catch {
      toast("No se pudo eliminar", "error")
    }
  }

  const handlePlay = async () => {
    try {
      const track = await api.getTrack(request.trackId)
      play(track, [track])
    } catch {
      toast("No se pudo reproducir", "error")
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-3">
      <div className="flex items-center gap-3">
        <CoverImage src={request.cover} alt={request.title} className="h-14 w-14" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{request.title}</p>
          <p className="truncate text-xs text-muted-foreground">{request.artist}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <StatusBadge status={request.status} progress={request.progress} />
            <span className="text-xs text-muted-foreground">{formatRelativeDate(request.createdAt)}</span>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {isDone && (
            <Button size="icon-sm" onClick={handlePlay} aria-label="Reproducir">
              <Play className="h-4 w-4 translate-x-0.5 fill-current" />
            </Button>
          )}
          {isFailed && (
            <Button size="icon-sm" variant="secondary" onClick={handleRetry} aria-label="Reintentar">
              <RotateCw className="h-4 w-4" />
            </Button>
          )}
          <Button size="icon-sm" variant="ghost" onClick={handleDelete} aria-label="Eliminar solicitud">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {isDownloading && typeof request.progress === "number" && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-status-downloading transition-[width] duration-500"
            style={{ width: `${request.progress}%` }}
          />
        </div>
      )}

      {isFailed && request.errorMessage && (
        <p className="mt-2 text-xs text-destructive">{request.errorMessage}</p>
      )}

      {showRequester && request.requestedByName && (
        <p className="mt-2 text-xs text-muted-foreground">Solicitado por {request.requestedByName}</p>
      )}
    </div>
  )
}
