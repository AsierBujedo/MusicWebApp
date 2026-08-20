"use client"

import * as React from "react"
import { useParams, useRouter } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { Play, Shuffle, Trash2, ArrowLeft, Music, Share2, ImagePlus, X, Users, Camera, ListOrdered, ChevronUp, ChevronDown, Save, ShieldCheck, MoreHorizontal } from "lucide-react"
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
import { Dropdown, DropdownItem } from "@/components/ui/dropdown"

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
  const [ordering, setOrdering] = React.useState(false)
  const [orderedTrackIds, setOrderedTrackIds] = React.useState<string[]>([])
  const [savingOrder, setSavingOrder] = React.useState(false)

  const addCollaborator = async () => {
    if (!data || !alias.trim()) return
    try {
      await api.addPlaylistCollaborator(data.id, alias.trim())
      setAlias("")
      mutate(); globalMutate("playlists")
      toast("Persona añadida", "success")
    } catch { toast("No se pudo añadir a esa persona", "error") }
  }
  const chooseFallbackCover = async (coverNumber: number) => { if (!data) return; try { const playlist = await api.setPlaylistFallbackCover(data.id, coverNumber); mutate(playlist, false); globalMutate("playlists"); setCoverPicker(false) } catch { toast("No se pudo cambiar la portada", "error") } }
  const uploadCover = async (file?: File) => { if (!data || !file) return; try { const playlist = await api.uploadPlaylistCover(data.id, file); mutate(playlist, false); globalMutate("playlists") } catch { toast("No se pudo subir la portada", "error") } }
  const resetCover = async () => { if (!data) return; try { const playlist = await api.resetPlaylistCover(data.id); mutate(playlist, false); globalMutate("playlists") } catch { toast("No se pudo restablecer la portada", "error") } }
  const removeCollaborator = async (username: string) => {
    if (!data) return
    try { await api.removePlaylistCollaborator(data.id, username); mutate(); globalMutate("playlists") }
    catch { toast("No se pudo eliminar a esa persona", "error") }
  }
  const setCollaboratorReorderPermission = async (username: string, canReorder: boolean) => {
    if (!data) return
    try {
      const playlist = await api.setPlaylistCollaboratorReorderPermission(data.id, username, canReorder)
      mutate(playlist, false)
      globalMutate("playlists")
      toast(canReorder ? "Autorización de orden concedida" : "Autorización de orden retirada", "success")
    } catch { toast("No se pudo actualizar la autorización", "error") }
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
  const isManager = !!data && (isOwner || data.collaborators?.some((person) => person.username === me?.username && person.canReorder))
  const orderedTracks = orderedTrackIds
    .map((trackId) => tracks.find((track) => track.id === trackId))
    .filter((track): track is Track => Boolean(track))

  const startOrdering = () => {
    setOrderedTrackIds(tracks.map((track) => track.id))
    setOrdering(true)
  }

  const moveTrack = (from: number, to: number) => {
    setOrderedTrackIds((current) => {
      if (to < 0 || to >= current.length) return current
      const next = [...current]
      const [trackId] = next.splice(from, 1)
      next.splice(to, 0, trackId)
      return next
    })
  }

  const saveOrder = async () => {
    if (!data || savingOrder) return
    setSavingOrder(true)
    try {
      const playlist = await api.reorderPlaylist(data.id, orderedTrackIds)
      mutate(playlist, false)
      globalMutate("playlists")
      setOrdering(false)
      toast("Orden de reproducción guardado", "success")
    } catch {
      toast("No se pudo guardar el orden", "error")
    } finally {
      setSavingOrder(false)
    }
  }

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
          <div className="flex w-40 shrink-0 flex-col gap-2 sm:w-48">
            <CoverImage src={data.cover} alt={data.name} className="h-40 w-40 shadow-xl sm:h-48 sm:w-48" />
            {isManager && <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"><Camera className="h-4 w-4" />Subir portada<input className="hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => uploadCover(event.target.files?.[0])} /></label>}
          </div>
          <div className="flex-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Playlist</p>
            <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl text-balance">{data.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">by {data.ownerUsername ?? "ti"}</p>
            {data.description && <p className="mt-2 text-sm text-muted-foreground text-pretty">{data.description}</p>}
            <p className="mt-2 text-sm text-muted-foreground">{tracks.length} canciones</p>

            <div className="mt-4 flex flex-wrap items-center gap-2">
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
              {isManager && tracks.length > 1 && (
                <Button variant="secondary" onClick={startOrdering} className="hidden gap-2 sm:inline-flex">
                  <ListOrdered className="h-4 w-4" />
                  Editar orden
                </Button>
              )}
              {isManager && <>
                <Button variant="ghost" size="icon" className="hidden sm:inline-flex" aria-label="Eliminar playlist" onClick={() => setConfirmDelete(true)}>
                  <Trash2 className="h-5 w-5" />
                </Button>
                <Button variant="ghost" size="icon" className="hidden sm:inline-flex" aria-label="Compartir playlist" onClick={() => setSharing(true)}>
                  <Share2 className="h-5 w-5" />
                </Button>
                <Button variant="ghost" size="icon" className="hidden sm:inline-flex" aria-label="Elegir carátula de una canción" onClick={() => setCoverPicker(true)}><ImagePlus className="h-5 w-5" /></Button>
                <Button variant="ghost" size="sm" className="hidden sm:inline-flex" onClick={() => void resetCover()}>Restablecer</Button>
                <Dropdown trigger={<Button variant="secondary" size="icon" className="sm:hidden" aria-label="Opciones de playlist"><MoreHorizontal className="h-5 w-5" /></Button>}>
                  {tracks.length > 1 && <DropdownItem icon={ListOrdered} onClick={startOrdering}>Editar orden</DropdownItem>}
                  <DropdownItem icon={Share2} onClick={() => setSharing(true)}>Compartir y permisos</DropdownItem>
                  <DropdownItem icon={ImagePlus} onClick={() => setCoverPicker(true)}>Elegir carátula</DropdownItem>
                  <DropdownItem icon={Camera} onClick={() => void resetCover()}>Restablecer carátula</DropdownItem>
                  <DropdownItem icon={Trash2} destructive onClick={() => setConfirmDelete(true)}>Eliminar playlist</DropdownItem>
                </Dropdown>
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
      ) : ordering ? (
        <section className="max-w-3xl rounded-2xl border border-border bg-card p-3 sm:p-4">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-display text-lg font-semibold">Orden de reproducción</h2>
              <p className="text-sm text-muted-foreground">Usa las flechas para decidir qué canción sonará después.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => setOrdering(false)} disabled={savingOrder}>Cancelar</Button>
              <Button onClick={() => void saveOrder()} disabled={savingOrder} className="gap-2"><Save className="h-4 w-4" />{savingOrder ? "Guardando…" : "Guardar orden"}</Button>
            </div>
          </div>
          <ol className="space-y-1">
            {orderedTracks.map((track, index) => (
              <li key={track.id} className="flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-secondary/60">
                <span className="w-6 shrink-0 text-center text-sm tabular-nums text-muted-foreground">{index + 1}</span>
                <CoverImage src={track.cover} alt="" className="h-11 w-11 shrink-0" />
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{track.title}</p><p className="truncate text-xs text-muted-foreground">{track.artist}</p></div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="icon-sm" aria-label={`Subir ${track.title}`} disabled={index === 0} onClick={() => moveTrack(index, index - 1)}><ChevronUp className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon-sm" aria-label={`Bajar ${track.title}`} disabled={index === orderedTracks.length - 1} onClick={() => moveTrack(index, index + 1)}><ChevronDown className="h-4 w-4" /></Button>
                </div>
              </li>
            ))}
          </ol>
        </section>
      ) : (
        <TrackList tracks={tracks} onRemove={handleRemove} />
      )}

      <Modal
        open={coverPicker}
        onClose={() => setCoverPicker(false)}
        title="Elegir carátula"
        description="Elige una de las carátulas predeterminadas que se asignan a las canciones sin portada."
      >
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">{Array.from({ length: 10 }, (_, index) => index + 1).map((coverNumber) => { const src = `/fallback-covers/abstract-${String(coverNumber).padStart(2, "0")}.webp`; return <button key={coverNumber} onClick={() => void chooseFallbackCover(coverNumber)} className="overflow-hidden rounded-xl border border-border hover:border-primary"><CoverImage src={src} alt={`Carátula ${coverNumber}`} className="aspect-square w-full" /></button> })}</div>
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
                <p className="mt-0.5 text-sm leading-5 text-muted-foreground">Añade personas por su alias. Las personas autorizadas podrán gestionar la playlist; solo tú podrás conceder autorizaciones.</p>
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
                  <div key={person.username} className="flex min-w-0 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm hover:bg-secondary/70"><Avatar name={person.displayName} src={person.avatar} className="h-8 w-8 text-xs" /><div className="min-w-0 flex-1"><span className="block truncate font-medium">@{person.username}</span>{person.canReorder && <span className="flex items-center gap-1 text-xs text-primary"><ShieldCheck className="h-3.5 w-3.5" />Autorizado para gestionar</span>}</div>{isManager && <div className="flex shrink-0 items-center gap-1">{isOwner && <Button variant={person.canReorder ? "secondary" : "ghost"} size="sm" onClick={() => void setCollaboratorReorderPermission(person.username, !person.canReorder)}>{person.canReorder ? "Quitar autorización" : "Autorizar"}</Button>}<Button variant="ghost" size="icon-sm" className="text-muted-foreground hover:text-status-failed" aria-label={`Eliminar a ${person.username}`} onClick={() => removeCollaborator(person.username)}><X className="h-4 w-4" /></Button></div>}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}
