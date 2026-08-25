"use client"

import * as React from "react"
import useSWR, { useSWRConfig } from "swr"
import { Plus, Check } from "lucide-react"
import type { Playlist, Track } from "@/types/api"
import { api, ApiError } from "@/lib/api"
import { useAuth } from "@/components/providers/auth-provider"
import { useToast } from "@/components/providers/toast-provider"
import { Modal } from "@/components/ui/modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { CoverImage } from "@/components/cover-image"

interface LibraryContextValue {
  favoriteIds: Set<string>
  isFavorite: (id: string) => boolean
  toggleFavorite: (track: Track) => Promise<void>
  requestTrack: (track: Track) => void
  downloadsAvailable: boolean
  addToPlaylist: (track: Track) => void
}

const LibraryContext = React.createContext<LibraryContextValue | null>(null)

function friendlyError(e: unknown): string {
  if (e instanceof ApiError) return e.message
  return "Ha ocurrido un problema. Inténtalo de nuevo."
}

export function LibraryProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const { toast } = useToast()
  const { mutate } = useSWRConfig()

  const { data: favorites } = useSWR<Track[]>(user ? "favorites" : null, () => api.getFavorites())
  const { data: playlists } = useSWR<Playlist[]>(user ? "playlists" : null, () => api.getPlaylists())
  const { data: downloadAvailability } = useSWR(user ? "downloads:availability" : null, () => api.getDownloadAvailability(), { refreshInterval: 30_000 })
  const downloadsAvailable = downloadAvailability?.enabled ?? true

  const favoriteIds = React.useMemo(() => new Set((favorites ?? []).map((t) => t.id)), [favorites])

  const [requestTarget, setRequestTarget] = React.useState<Track | null>(null)
  const [requesting, setRequesting] = React.useState(false)
  const [playlistTarget, setPlaylistTarget] = React.useState<Track | null>(null)
  const [newPlaylistName, setNewPlaylistName] = React.useState("")
  const writablePlaylists = React.useMemo(
    () => (playlists ?? []).filter((playlist) =>
      playlist.ownerUsername === user?.username || playlist.collaborators?.some((person) => person.username === user?.username && person.canReorder),
    ),
    [playlists, user?.username],
  )

  const isFavorite = React.useCallback((id: string) => favoriteIds.has(id), [favoriteIds])

  const toggleFavorite = React.useCallback(
    async (track: Track) => {
      const currentlyFav = favoriteIds.has(track.id)
      try {
        if (currentlyFav) {
          await api.removeFavorite(track.id)
          toast("Quitado de favoritos", "info")
        } else {
          await api.addFavorite(track.id)
          toast("Añadido a favoritos", "success")
        }
        mutate("favorites")
      } catch (e) {
        toast(friendlyError(e), "error")
      }
    },
    [favoriteIds, mutate, toast],
  )

  const confirmRequest = React.useCallback(async () => {
    if (!requestTarget || !downloadsAvailable) return
    setRequesting(true)
    try {
      await api.createRequest({ type: "track", trackId: requestTarget.id })
      toast("Solicitud enviada", "success")
      setRequestTarget(null)
      mutate("requests")
      mutate((key) => typeof key === "string" && key.startsWith("search:"))
      mutate((key) => typeof key === "string" && key.startsWith("playlist:"))
    } catch (e) {
      toast(friendlyError(e), "error")
    } finally {
      setRequesting(false)
    }
  }, [requestTarget, mutate, toast])

  const handleAddToPlaylist = React.useCallback(
    async (playlistId: string) => {
      if (!playlistTarget) return
      try {
        await api.addTrackToPlaylist(playlistId, playlistTarget.id)
        toast("Añadida a la playlist", "success")
        setPlaylistTarget(null)
        mutate("playlists")
        mutate(`playlist:${playlistId}`)
      } catch (e) {
        toast(friendlyError(e), "error")
      }
    },
    [playlistTarget, mutate, toast],
  )

  const handleCreateAndAdd = React.useCallback(async () => {
    if (!playlistTarget || !newPlaylistName.trim()) return
    try {
      const pl = await api.createPlaylist(newPlaylistName.trim())
      await api.addTrackToPlaylist(pl.id, playlistTarget.id)
      toast("Playlist creada y canción añadida", "success")
      setNewPlaylistName("")
      setPlaylistTarget(null)
      mutate("playlists")
    } catch (e) {
      toast(friendlyError(e), "error")
    }
  }, [playlistTarget, newPlaylistName, mutate, toast])

  const value: LibraryContextValue = {
    favoriteIds,
    isFavorite,
    toggleFavorite,
    requestTrack: setRequestTarget,
    downloadsAvailable,
    addToPlaylist: setPlaylistTarget,
  }

  return (
    <LibraryContext.Provider value={value}>
      {children}

      {/* Confirm request modal */}
      <Modal
        open={Boolean(requestTarget)}
        onClose={() => setRequestTarget(null)}
        title="¿Quieres solicitar esta canción?"
        description="Nos pondremos a buscarla. Te avisaremos cuando esté lista para escuchar."
      >
        {requestTarget && (
          <div className="space-y-5">
            <div className="flex items-center gap-4 rounded-2xl bg-secondary/60 p-3">
              <CoverImage src={requestTarget.cover} alt={requestTarget.title} className="h-14 w-14" />
              <div className="min-w-0">
                <p className="truncate font-medium">{requestTarget.title}</p>
                <p className="truncate text-sm text-muted-foreground">{requestTarget.artist}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" className="flex-1" onClick={() => setRequestTarget(null)}>
                Cancelar
              </Button>
              <Button className="flex-1" onClick={confirmRequest} disabled={requesting}>
                {requesting ? "Enviando…" : "Solicitar"}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Add to playlist modal */}
      <Modal
        open={Boolean(playlistTarget)}
        onClose={() => setPlaylistTarget(null)}
        title="Añadir a una playlist"
      >
        {playlistTarget && (
          <div className="space-y-4">
            <div className="max-h-64 space-y-1 overflow-y-auto no-scrollbar">
              {writablePlaylists.map((pl) => {
                const already = pl.trackIds.includes(playlistTarget.id)
                return (
                  <button
                    key={pl.id}
                    onClick={() => !already && handleAddToPlaylist(pl.id)}
                    disabled={already}
                    className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition-colors hover:bg-secondary disabled:opacity-60"
                  >
                    <CoverImage src={pl.cover} alt={pl.name} className="h-11 w-11" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{pl.name}</p>
                      <p className="text-xs text-muted-foreground">{pl.trackIds.length} canciones</p>
                    </div>
                    {already && <Check className="h-4 w-4 text-status-available" />}
                  </button>
                )
              })}
              {writablePlaylists.length === 0 && (
                <p className="px-2 py-4 text-center text-sm text-muted-foreground">No tienes ninguna playlist propia o autorizada.</p>
              )}
            </div>
            <div className="flex items-center gap-2 border-t border-border pt-4">
              <Input
                value={newPlaylistName}
                onChange={(e) => setNewPlaylistName(e.target.value)}
                placeholder="Crear nueva playlist…"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.nativeEvent.isComposing) handleCreateAndAdd()
                }}
              />
              <Button size="icon" aria-label="Crear playlist" onClick={handleCreateAndAdd} disabled={!newPlaylistName.trim()}>
                <Plus className="h-5 w-5" />
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </LibraryContext.Provider>
  )
}

export function useLibrary() {
  const ctx = React.useContext(LibraryContext)
  if (!ctx) throw new Error("useLibrary must be used within LibraryProvider")
  return ctx
}
