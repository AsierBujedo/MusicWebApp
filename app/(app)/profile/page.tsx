"use client"

import * as React from "react"
import useSWR, { useSWRConfig } from "swr"
import { LogOut, Heart, ListMusic, Inbox, Shield, Moon, Sun, ChevronRight, KeyRound, Music2, Check } from "lucide-react"
import Link from "next/link"
import type { HistoryEntry, Playlist, Track, MusicRequest } from "@/types/api"
import { api } from "@/lib/api"
import { useAuth } from "@/components/providers/auth-provider"
import { useTheme } from "@/components/providers/theme-provider"
import { PageHeader } from "@/components/page-header"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { ChangePasswordModal } from "@/components/change-password-modal"
import { Modal } from "@/components/ui/modal"
import { useToast } from "@/components/providers/toast-provider"
import type { SpotifyPlaylist, SpotifyStatus } from "@/lib/api-types"

export default function ProfilePage() {
  const { user, isAdmin, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const { toast } = useToast()
  const { mutate: globalMutate } = useSWRConfig()
  const [passwordOpen, setPasswordOpen] = React.useState(false)
  const [spotifyOpen, setSpotifyOpen] = React.useState(false)
  const [selectedSpotifyPlaylists, setSelectedSpotifyPlaylists] = React.useState<string[]>([])
  const [importingSpotify, setImportingSpotify] = React.useState(false)

  const { data: favorites } = useSWR<Track[]>(user ? "favorites" : null, () => api.getFavorites())
  const { data: playlists } = useSWR<Playlist[]>(user ? "playlists" : null, () => api.getPlaylists())
  const { data: requests } = useSWR<MusicRequest[]>(user ? "requests" : null, () => api.getRequests())
  const { data: history } = useSWR<HistoryEntry[]>(user ? "history" : null, () => api.getHistory())
  const { data: spotifyStatus } = useSWR<SpotifyStatus>(
    user ? "spotify:status" : null,
    () => api.getSpotifyStatus(),
  )
  const { data: spotifyPlaylists, isLoading: loadingSpotifyPlaylists } = useSWR<SpotifyPlaylist[]>(
    spotifyOpen && spotifyStatus?.connected ? "spotify:playlists" : null,
    () => api.getSpotifyPlaylists(),
  )

  if (!user) return null

  const stats = [
    { icon: Heart, label: "Favoritos", value: favorites?.length ?? 0, href: "/favorites" },
    { icon: ListMusic, label: "Playlists", value: playlists?.length ?? 0, href: "/playlists" },
    { icon: Inbox, label: "Solicitudes", value: requests?.length ?? 0, href: "/requests" },
  ]

  const connectSpotify = async () => {
    try {
      const { authorizationUrl } = await api.connectSpotify()
      window.location.assign(authorizationUrl)
    } catch {
      toast("No se pudo iniciar la conexión con Spotify", "error")
    }
  }

  const toggleSpotifyPlaylist = (playlistId: string) => {
    setSelectedSpotifyPlaylists((selected) =>
      selected.includes(playlistId) ? selected.filter((id) => id !== playlistId) : [...selected, playlistId],
    )
  }

  const importSpotifyPlaylists = async () => {
    if (!selectedSpotifyPlaylists.length) return
    setImportingSpotify(true)
    try {
      const result = await api.importSpotifyPlaylists(selectedSpotifyPlaylists)
      toast(`${result.importedPlaylists} playlist${result.importedPlaylists === 1 ? "" : "s"} importada${result.importedPlaylists === 1 ? "" : "s"}`, "success")
      setSpotifyOpen(false)
      setSelectedSpotifyPlaylists([])
      globalMutate("playlists")
    } catch {
      toast("No se pudieron importar las playlists seleccionadas", "error")
    } finally {
      setImportingSpotify(false)
    }
  }

  return (
    <div>
      <PageHeader title="Mi perfil" />

      <div className="mb-8 flex flex-col items-center gap-4 rounded-3xl border border-border bg-card p-8 text-center sm:flex-row sm:text-left">
        <Avatar name={user.displayName} src={user.avatar} className="h-20 w-20 text-2xl" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-center gap-2 sm:justify-start">
            <h2 className="text-xl font-semibold">{user.displayName}</h2>
            {isAdmin && (
              <span className="flex items-center gap-1 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-primary">
                <Shield className="h-3 w-3" />
                Admin
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">@{user.username}</p>
          {user.email && <p className="text-sm text-muted-foreground">{user.email}</p>}
        </div>
        <Button variant="secondary" onClick={() => logout()} className="gap-2">
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </Button>
      </div>

      <div className="mb-8 grid grid-cols-3 gap-3">
        {stats.map((s) => {
          const Icon = s.icon
          return (
            <Link
              key={s.label}
              href={s.href}
              className="flex flex-col items-center gap-1 rounded-2xl border border-border bg-card p-4 transition-colors hover:border-primary/50"
            >
              <Icon className="h-5 w-5 text-primary" />
              <span className="text-2xl font-semibold tabular-nums">{s.value}</span>
              <span className="text-xs text-muted-foreground">{s.label}</span>
            </Link>
          )
        })}
      </div>

      <div className="space-y-2">
        <h3 className="px-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Preferencias</h3>
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <button
            onClick={toggle}
            className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-secondary"
          >
            {theme === "dark" ? <Moon className="h-5 w-5 text-muted-foreground" /> : <Sun className="h-5 w-5 text-muted-foreground" />}
            <div className="flex-1">
              <p className="text-sm font-medium">Tema</p>
              <p className="text-xs text-muted-foreground">{theme === "dark" ? "Oscuro" : "Claro"}</p>
            </div>
            <span className="text-sm text-muted-foreground">Cambiar</span>
          </button>

          <button
            onClick={() => (spotifyStatus?.connected ? setSpotifyOpen(true) : void connectSpotify())}
            disabled={spotifyStatus?.configured === false}
            className="flex w-full items-center gap-3 border-t border-border px-4 py-3.5 text-left transition-colors hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-55"
          >
            <Music2 className="h-5 w-5 text-[#1ed760]" />
            <div className="flex-1">
              <p className="text-sm font-medium">Spotify</p>
              <p className="text-xs text-muted-foreground">
                {spotifyStatus?.configured === false
                  ? "No configurado en el servidor"
                  : spotifyStatus?.connected
                    ? "Importar playlists de tu cuenta"
                    : "Conecta tu cuenta para importar playlists"}
              </p>
            </div>
            {spotifyStatus?.connected ? <ChevronRight className="h-5 w-5 text-muted-foreground" /> : <span className="text-sm text-primary">Conectar</span>}
          </button>

          {isAdmin && (
            <Link
              href="/admin"
              className="flex w-full items-center gap-3 border-t border-border px-4 py-3.5 transition-colors hover:bg-secondary"
            >
              <Shield className="h-5 w-5 text-muted-foreground" />
              <div className="flex-1">
                <p className="text-sm font-medium">Panel de administración</p>
                <p className="text-xs text-muted-foreground">Usuarios, solicitudes y servicios</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </Link>
          )}
        </div>
      </div>

      <div className="mt-6 space-y-2">
        <h3 className="px-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Seguridad</h3>
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <button
            onClick={() => setPasswordOpen(true)}
            className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-secondary"
          >
            <KeyRound className="h-5 w-5 text-muted-foreground" />
            <div className="flex-1">
              <p className="text-sm font-medium">Cambiar contraseña</p>
              <p className="text-xs text-muted-foreground">Actualiza la contraseña de tu cuenta</p>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>
      </div>

      <p className="mt-6 text-center text-xs text-muted-foreground">
        {history?.length ?? 0} reproducciones registradas · Resonar
      </p>

      <ChangePasswordModal open={passwordOpen} onClose={() => setPasswordOpen(false)} />

      <Modal
        open={spotifyOpen}
        onClose={() => !importingSpotify && setSpotifyOpen(false)}
        title="Importar desde Spotify"
        description="Elige las playlists que quieres copiar a Resonar. Se importarán sus canciones y las que no estén en tu biblioteca quedarán disponibles para solicitar."
        className="max-w-2xl"
      >
        {loadingSpotifyPlaylists ? (
          <p className="py-8 text-center text-sm text-muted-foreground">Cargando tus playlists de Spotify…</p>
        ) : spotifyPlaylists?.length ? (
          <div className="space-y-4">
            <div className="max-h-[52vh] space-y-1 overflow-y-auto rounded-xl border border-border p-1.5">
              {spotifyPlaylists.map((playlist) => {
                const selected = selectedSpotifyPlaylists.includes(playlist.id)
                return (
                  <button
                    key={playlist.id}
                    type="button"
                    onClick={() => toggleSpotifyPlaylist(playlist.id)}
                    className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-secondary"
                  >
                    <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${selected ? "border-[#1ed760] bg-[#1ed760] text-black" : "border-muted-foreground/50"}`}>
                      {selected && <Check className="h-3.5 w-3.5 stroke-[3]" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{playlist.name}</span>
                      <span className="block truncate text-xs text-muted-foreground">{playlist.trackCount} canciones{playlist.ownerName ? ` · ${playlist.ownerName}` : ""}</span>
                    </span>
                  </button>
                )
              })}
            </div>
            <div className="flex items-center justify-between gap-3">
              <button type="button" onClick={() => setSelectedSpotifyPlaylists(spotifyPlaylists.map((playlist) => playlist.id))} className="text-sm text-primary hover:underline">Seleccionar todas</button>
              <Button onClick={() => void importSpotifyPlaylists()} disabled={!selectedSpotifyPlaylists.length || importingSpotify}>
                {importingSpotify ? "Importando…" : `Importar ${selectedSpotifyPlaylists.length || ""} playlist${selectedSpotifyPlaylists.length === 1 ? "" : "s"}`}
              </Button>
            </div>
          </div>
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">No se encontraron playlists en esta cuenta.</p>
        )}
      </Modal>
    </div>
  )
}
