"use client"

import * as React from "react"
import { useParams, useRouter } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { Play, Shuffle, Trash2, ArrowLeft, Music } from "lucide-react"
import type { Playlist, Track } from "@/types/api"
import { api, ApiError } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { useToast } from "@/components/providers/toast-provider"
import { TrackList, TrackListSkeleton } from "@/components/track-list"
import { EmptyState } from "@/components/empty-state"
import { CoverImage } from "@/components/cover-image"
import { Button } from "@/components/ui/button"
import { Modal } from "@/components/ui/modal"

export default function PlaylistDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { playQueue, toggleShuffle } = usePlayer()
  const { toast } = useToast()
  const { mutate: globalMutate } = useSWRConfig()

  const { data, error, isLoading, mutate } = useSWR<Playlist>(
    id ? `playlist:${id}` : null,
    () => api.getPlaylist(id),
  )

  const [confirmDelete, setConfirmDelete] = React.useState(false)

  if (error instanceof ApiError && error.status === 404) {
    return (
      <EmptyState
        icon={Music}
        title="Playlist no encontrada"
        description="Puede que se haya eliminado."
        action={
          <Button onClick={() => router.push("/playlists")} variant="secondary">
            Volver a playlists
          </Button>
        }
      />
    )
  }

  const tracks = data?.tracks ?? []
  const playable = tracks.filter((t) => t.status === "AVAILABLE")

  const handleRemove = async (track: Track) => {
    if (!data) return
    // optimistic
    mutate({ ...data, tracks: tracks.filter((t) => t.id !== track.id), trackIds: data.trackIds.filter((t) => t !== track.id) }, false)
    try {
      await api.removeTrackFromPlaylist(data.id, track.id)
      toast("Quitada de la playlist", "info")
      mutate()
      globalMutate("playlists")
    } catch {
      toast("No se pudo quitar", "error")
      mutate()
    }
  }

  const handleDelete = async () => {
    if (!data) return
    try {
      await api.deletePlaylist(data.id)
      toast("Playlist eliminada", "info")
      globalMutate("playlists")
      router.push("/playlists")
    } catch {
      toast("No se pudo eliminar", "error")
    }
  }

  return (
    <div>
      <button
        onClick={() => router.push("/playlists")}
        className="mb-4 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Playlists
      </button>

      {isLoading ? (
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="skeleton h-40 w-40 rounded-2xl" />
          <div className="flex-1 space-y-3">
            <div className="skeleton h-8 w-1/2 rounded" />
            <div className="skeleton h-4 w-1/3 rounded" />
          </div>
        </div>
      ) : data ? (
        <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end">
          <CoverImage src={data.cover} alt={data.name} className="h-40 w-40 shadow-xl sm:h-48 sm:w-48" />
          <div className="flex-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Playlist</p>
            <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl text-balance">{data.name}</h1>
            {data.description && <p className="mt-2 text-sm text-muted-foreground text-pretty">{data.description}</p>}
            <p className="mt-2 text-sm text-muted-foreground">{tracks.length} canciones</p>

            <div className="mt-4 flex items-center gap-2">
              <Button
                onClick={() => playQueue(playable)}
                disabled={playable.length === 0}
                className="gap-2"
              >
                <Play className="h-4 w-4 fill-current" />
                Reproducir
              </Button>
              <Button
                variant="secondary"
                size="icon"
                aria-label="Aleatorio"
                disabled={playable.length === 0}
                onClick={() => { toggleShuffle(); playQueue(playable) }}
              >
                <Shuffle className="h-5 w-5" />
              </Button>
              <Button variant="ghost" size="icon" aria-label="Eliminar playlist" onClick={() => setConfirmDelete(true)}>
                <Trash2 className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <TrackListSkeleton count={5} />
      ) : tracks.length === 0 ? (
        <EmptyState
          icon={Music}
          title="Playlist vacía"
          description="Añade canciones desde el buscador o con el menú de cualquier canción."
        />
      ) : (
        <TrackList tracks={tracks} onRemove={handleRemove} />
      )}

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="¿Eliminar esta playlist?"
        description="Esta acción no se puede deshacer."
      >
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" onClick={() => setConfirmDelete(false)}>
            Cancelar
          </Button>
          <Button variant="danger" className="flex-1" onClick={handleDelete}>
            Eliminar
          </Button>
        </div>
      </Modal>
    </div>
  )
}
