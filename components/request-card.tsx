"use client"

import { RotateCw, Trash2, Play, Upload, Youtube } from "lucide-react"
import { useRef, useState } from "react"
import type { MusicRequest } from "@/types/api"
import { api } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { useToast } from "@/components/providers/toast-provider"
import { CoverImage } from "@/components/cover-image"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { formatRelativeDate } from "@/lib/utils"
import { useSWRConfig } from "swr"
import { useAuth } from "@/components/providers/auth-provider"
import { Modal } from "@/components/ui/modal"
import type { YouTubeCandidate } from "@/lib/api-types"

export function RequestCard({ request, showRequester }: { request: MusicRequest; showRequester?: boolean }) {
  const { play } = usePlayer()
  const { toast } = useToast()
  const { mutate } = useSWRConfig()
  const { user, isAdmin } = useAuth()
  const fileInput = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [youtubeOpen, setYoutubeOpen] = useState(false)
  const [youtubeLoading, setYoutubeLoading] = useState(false)
  const [youtubeDownloading, setYoutubeDownloading] = useState<string | null>(null)
  const [youtubeCandidates, setYoutubeCandidates] = useState<YouTubeCandidate[]>([])

  const isDownloading = request.status === "DOWNLOADING"
  const isDone = request.status === "AVAILABLE"
  const isFailed = request.status === "FAILED" || request.status === "REJECTED"
  const scheduledSoulseekRetry = request.soulseekRetryAt && new Date(request.soulseekRetryAt).getTime() > Date.now()

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

  const handleUpload = async (file?: File) => {
    if (!file) return
    setUploading(true)
    try {
      await api.uploadRequestAudio(request.id, file)
      toast("Archivo importado y etiquetado por Resonar", "success")
      refresh()
    } catch {
      toast("No se pudo importar el archivo. Usa un MP3 o FLAC válido.", "error")
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ""
    }
  }

  const canUpload = request.status === "FAILED" && (isAdmin || request.requestedBy === user?.id)

  const openYouTubeFallback = async () => {
    setYoutubeOpen(true)
    setYoutubeLoading(true)
    setYoutubeCandidates([])
    try {
      setYoutubeCandidates(await api.getYouTubeCandidates(request.id))
    } catch {
      toast("No se pudieron buscar alternativas en YouTube.", "error")
      setYoutubeOpen(false)
    } finally {
      setYoutubeLoading(false)
    }
  }

  const selectYouTubeCandidate = async (candidate: YouTubeCandidate) => {
    setYoutubeDownloading(candidate.videoId)
    try {
      await api.downloadRequestFromYouTube(request.id, candidate.videoId)
      toast("Audio descargado y etiquetado por Resonar", "success")
      setYoutubeOpen(false)
      refresh()
    } catch {
      toast("No se pudo descargar el audio seleccionado.", "error")
    } finally {
      setYoutubeDownloading(null)
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
          {canUpload && (
            <>
              <input
                ref={fileInput}
                className="hidden"
                type="file"
                accept="audio/mpeg,audio/flac,.mp3,.flac"
                onChange={(event) => void handleUpload(event.target.files?.[0])}
              />
              <Button size="icon-sm" variant="secondary" disabled={uploading} onClick={() => fileInput.current?.click()} aria-label="Subir archivo propio" title="Subir MP3 o FLAC propio">
                <Upload className="h-4 w-4" />
              </Button>
            </>
          )}
          {canUpload && (
            <Button size="icon-sm" variant="secondary" onClick={() => void openYouTubeFallback()} aria-label="Último recurso: buscar en YouTube" title="Último recurso: buscar en YouTube">
              <Youtube className="h-4 w-4" />
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

      {scheduledSoulseekRetry && (
        <p className="mt-1 text-xs text-status-pending">
          Próximo intento: {new Date(request.soulseekRetryAt!).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
          {request.soulseekRetryCount ? ` · intento automático ${request.soulseekRetryCount}` : ""}
        </p>
      )}

      {showRequester && request.requestedByName && (
        <p className="mt-2 text-xs text-muted-foreground">Solicitado por {request.requestedByName}</p>
      )}

      <Modal
        open={youtubeOpen}
        onClose={() => !youtubeDownloading && setYoutubeOpen(false)}
        title="Último recurso: YouTube"
        description={`Elige una coincidencia para “${request.title}”. Se descargará solo la opción seleccionada y Resonar sustituirá sus metadatos y portada.`}
        className="max-w-xl"
      >
        {youtubeLoading ? (
          <p className="py-6 text-center text-sm text-muted-foreground">Buscando alternativas…</p>
        ) : youtubeCandidates.length ? (
          <div className="max-h-[55vh] space-y-2 overflow-y-auto pr-1">
            {youtubeCandidates.map((candidate) => (
              <button
                key={candidate.videoId}
                type="button"
                disabled={Boolean(youtubeDownloading)}
                onClick={() => void selectYouTubeCandidate(candidate)}
                className="flex w-full items-center gap-3 rounded-xl border border-border p-3 text-left transition-colors hover:bg-secondary disabled:opacity-60"
              >
                <Youtube className="h-5 w-5 shrink-0 text-destructive" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{candidate.title}</span>
                  <span className="block truncate text-xs text-muted-foreground">{candidate.channel}{candidate.duration ? ` · ${Math.floor(candidate.duration / 60)}:${String(candidate.duration % 60).padStart(2, "0")}` : ""}</span>
                </span>
                {youtubeDownloading === candidate.videoId && <span className="text-xs text-muted-foreground">Descargando…</span>}
              </button>
            ))}
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-muted-foreground">No se encontraron coincidencias.</p>
        )}
      </Modal>
    </div>
  )
}
