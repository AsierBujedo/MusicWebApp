"use client"

import * as React from "react"
import { useParams, useRouter } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { Play, Shuffle, Trash2, ArrowLeft, Music, Share2, ImagePlus, X, Users } from "lucide-react"
import type { Playlist, Track } from "@/types/api"
import { api, ApiError } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { useToast } from "@/components/providers/toast-provider"
import { useAuth } from "@/components/providers/auth-provider"
import { TrackList, TrackListSkeleton } from "@/components/track-list"
import { EmptyState } from "@/components/empty-state"
import { CoverImage } from "@/components/cover-image"
import { Button } from "@/components/ui/button"
import { Modal } from "@/components/ui/modal"
import { Input } from "@/components/ui/input"
import { Avatar } from "@/components/ui/avatar"

export default function PlaylistDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { playQueue, toggleShuffle } = usePlayer()
  const { toast } = useToast()
  const { user: me } = useAuth()
  const { mutate: globalMutate } = useSWRConfig()

  const { data, error, isLoading, mutate } = useSWR<Playlist>(
    id ? `playlist:${id}` : null,
    () => api.getPlaylist(id),
    {
      // SSE normally refreshes this cache immediately. Poll only while the
      // playlist has pending downloads as a resilient fallback for a mobile
      // browser/PWA that temporarily drops its EventSource connection.
      refreshInterval: (playlist) =>
        playlist?.tracks?.some((track) => track.status === "PENDING" || track.status === "DOWNLOADING") ? 5_000 : 0,
    },
  )

  const [confirmDelete, setConfirmDelete] = React.useState(false)
  const [sharing, setSharing] = React.useState(false)
  const [alias, setAlias] = React.useState("")
  const [coverPicker, setCoverPicker] = React.useState(false)

  const addCollaborator = async () => {
    if (!data || !alias.trim()) return
    try {
      await api.addPlaylistCollaborator(data.id, alias.trim())
      setAlias("")
      mutate(); globalMutate("playlists")
      toast("Persona añadida", "success")
    } catch { toast("No se pudo añadir a esa persona", "error") }
  }
  const chooseTrackCover = async (trackId: string) => { if (!data) return; try { await api.setPlaylistCoverFromTrack(data.id, trackId); mutate(); globalMutate("playlists"); setCoverPicker(false) } catch { toast("No se pudo cambiar la portada", "error") } }
  const resetCover = async () => { if (!data) return; try { await api.resetPlaylistCover(data.id); mutate(); globalMutate("playlists") } catch { toast("No se pudo restablecer la portada", "error") } }
  const removeCollaborator = async (username: string) => {
    if (!data) return
    try { await api.removePlaylistCollaborator(data.id, username); mutate(); globalMutate("playlists") }
    catch { toast("No se pudo eliminar a esa persona", "error") }
  }

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
  const isOwner = !!data && data.ownerUsername === me?.username

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
            <p className="mt-1 text-sm text-muted-foreground">by {data.ownerUsername ?? "ti"}</p>
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
              {isOwner && <>
                <Button variant="ghost" size="icon" aria-label="Eliminar playlist" onClick={() => setConfirmDelete(true)}>
                  <Trash2 className="h-5 w-5" />
                </Button>
                <Button variant="ghost" size="icon" aria-label="Compartir playlist" onClick={() => setSharing(true)}>
                  <Share2 className="h-5 w-5" />
                </Button>
                <Button variant="ghost" size="icon" aria-label="Elegir carátula de una canción" onClick={() => setCoverPicker(true)}><ImagePlus className="h-5 w-5" /></Button>
                <Button variant="ghost" size="sm" onClick={() => void resetCover()}>Restablecer</Button>
              </>}
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
        open={coverPicker}
        onClose={() => setCoverPicker(false)}
        title="Elegir carátula"
        description="Selecciona la portada de una canción de esta playlist o restablece el collage automático."
      >
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">{tracks.filter((track) => track.cover).map((track) => <button key={track.id} onClick={() => void chooseTrackCover(track.id)} className="overflow-hidden rounded-xl border border-border hover:border-primary"><CoverImage src={track.cover} alt={track.title} className="aspect-square w-full" /></button>)}</div>
      </Modal>

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
      <Modal open={sharing} onClose={() => setSharing(false)} title="Compartir playlist" className="max-w-xl">
        <div className="space-y-5">
          <div className="rounded-2xl border border-border bg-secondary/40 p-4">
            <div className="flex gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"><Users className="h-5 w-5" /></div>
              <div>
                <p className="text-sm font-medium">Edición compartida</p>
                <p className="mt-0.5 text-sm leading-5 text-muted-foreground">Añade personas por su alias. Podrán añadir y quitar canciones de esta playlist.</p>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <label htmlFor="playlist-collaborator" className="text-sm font-medium">Añadir persona</label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input id="playlist-collaborator" value={alias} onChange={(e) => setAlias(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addCollaborator()} placeholder="@marta" className="min-w-0 flex-1" />
              <Button onClick={addCollaborator} className="w-full shrink-0 sm:w-auto">Añadir</Button>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Personas con acceso <span className="text-muted-foreground">({data?.collaboratorUsernames?.length ?? 0})</span></p>
            {(data?.collaboratorUsernames?.length ?? 0) === 0 ? (
              <p className="rounded-xl border border-dashed border-border px-4 py-5 text-center text-sm text-muted-foreground">Aún no has añadido a nadie.</p>
            ) : (
              <div className="max-h-52 space-y-1 overflow-y-auto rounded-xl border border-border p-1.5">
                {(data?.collaborators ?? (data?.collaboratorUsernames ?? []).map((username) => ({ username, displayName: username }))).map((person) => (
                  <div key={person.username} className="flex min-w-0 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm hover:bg-secondary/70"><Avatar name={person.displayName} src={person.avatar} className="h-8 w-8 text-xs" /><span className="min-w-0 flex-1 truncate font-medium">@{person.username}</span>{isOwner && <Button variant="ghost" size="icon-sm" className="shrink-0 text-muted-foreground hover:text-status-failed" aria-label={`Eliminar a ${person.username}`} onClick={() => removeCollaborator(person.username)}><X className="h-4 w-4" /></Button>}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}
