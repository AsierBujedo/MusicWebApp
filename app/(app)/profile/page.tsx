"use client"

import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { LogOut, Heart, ListMusic, Inbox, Shield, Moon, Sun, ChevronRight, KeyRound, Music2, Check, Camera, Mail } from "lucide-react"
import Link from "next/link"
import type { HistoryEntry, Playlist, Track, MusicRequest, User } from "@/types/api"
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
import { Input } from "@/components/ui/input"

export default function ProfilePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, isAdmin, hasFeature, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const { toast } = useToast()
  const { mutate: globalMutate } = useSWRConfig()
  const [passwordOpen, setPasswordOpen] = React.useState(false)
  const [emailOpen, setEmailOpen] = React.useState(false)
  const [email, setEmail] = React.useState("")
  const [savingEmail, setSavingEmail] = React.useState(false)
  const [spotifyOpen, setSpotifyOpen] = React.useState(false)
  const [selectedSpotifyPlaylists, setSelectedSpotifyPlaylists] = React.useState<string[]>([])
  const [importingSpotify, setImportingSpotify] = React.useState(false)
  const [demoOpen, setDemoOpen] = React.useState(false)
  const avatarInput = React.useRef<HTMLInputElement>(null)

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
  const { data: demoUsers } = useSWR<User[]>(demoOpen && hasFeature("admin.demo") ? "demo:users" : null, () => api.getDemoUsers())

  React.useEffect(() => {
    const outcome = searchParams.get("spotify")
    if (!outcome) return
    if (outcome === "connected") {
      // Wait for the fresh status request; otherwise the query would be
      // removed before the OAuth connection is visible to the frontend.
      if (!spotifyStatus) return
      if (spotifyStatus.connected) {
        setSpotifyOpen(true)
        toast("Spotify conectado. Elige las playlists que quieres importar.", "success")
      } else {
        toast("Spotify se conectó, pero no pudimos recuperar la sesión", "error")
      }
    } else if (outcome === "error") {
      toast("No se pudo completar la conexión con Spotify", "error")
    } else if (outcome === "denied") {
      toast("Cancelaste la conexión con Spotify", "info")
    }
    router.replace("/profile")
  }, [router, searchParams, spotifyStatus?.connected, toast])

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
  const uploadAvatar = async (file?: File) => { if (!file) return; try { await api.uploadAvatar(file); await globalMutate("auth:me"); toast("Foto de perfil actualizada", "success") } catch { toast("No se pudo subir la foto", "error") } finally { if (avatarInput.current) avatarInput.current.value = "" } }
  const openEmail = () => { setEmail(user.email ?? ""); setEmailOpen(true) }
  const saveEmail = async (event: React.FormEvent) => { event.preventDefault(); if (!email.trim()) return; setSavingEmail(true); try { await api.updateProfileEmail(email); await globalMutate("auth:me"); setEmailOpen(false); toast("Correo actualizado", "success") } catch { toast("No se pudo actualizar el correo", "error") } finally { setSavingEmail(false) } }
  const startDemo = async (target: User) => { try { await api.startDemo(target.id); await globalMutate("auth:me"); await globalMutate("demo:status"); setDemoOpen(false); toast(`Modo demo: @${target.username}`, "info"); router.push("/") } catch { toast("No se pudo iniciar el modo demo", "error") } }

  return (
    <div>
      <PageHeader title="Mi perfil" />

      <div className="mb-8 flex flex-col items-center gap-4 rounded-3xl border border-border bg-card p-8 text-center sm:flex-row sm:text-left">
        <div className="relative"><Avatar name={user.displayName} src={user.avatar} className="h-20 w-20 text-2xl" /><button onClick={() => avatarInput.current?.click()} className="absolute -bottom-1 -right-1 rounded-full bg-primary p-1.5 text-primary-foreground" aria-label="Cambiar foto"><Camera className="h-3.5 w-3.5" /></button><input ref={avatarInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(e) => void uploadAvatar(e.target.files?.[0])} /></div>
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
          <p className="text-sm text-muted-foreground">{user.email ?? "Correo no añadido"}</p>
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
          {hasFeature("admin.demo") && <button onClick={() => setDemoOpen(true)} className="flex w-full items-center gap-3 border-t border-border px-4 py-3.5 text-left transition-colors hover:bg-secondary"><Shield className="h-5 w-5 text-muted-foreground" /><div className="flex-1"><p className="text-sm font-medium">Modo demo</p><p className="text-xs text-muted-foreground">Entrar temporalmente como otra persona</p></div><ChevronRight className="h-5 w-5 text-muted-foreground" /></button>}
        </div>
      </div>

      <Modal open={demoOpen} onClose={() => setDemoOpen(false)} title="Modo demo" description="Operarás temporalmente como esta persona. Podrás volver a tu cuenta desde el aviso superior.">
        <div className="max-h-80 space-y-1 overflow-y-auto">{demoUsers?.map((target) => <button key={target.id} onClick={() => void startDemo(target)} className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left hover:bg-secondary"><Avatar name={target.displayName} src={target.avatar} className="h-9 w-9" /><span className="min-w-0"><span className="block truncate text-sm font-medium">{target.displayName}</span><span className="block text-xs text-muted-foreground">@{target.username}</span></span></button>)}</div>
      </Modal>

      <div className="mt-6 space-y-2">
        <h3 className="px-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Cuenta y seguridad</h3>
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          <button
            onClick={openEmail}
            className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-secondary"
          >
            <Mail className="h-5 w-5 text-muted-foreground" />
            <div className="flex-1"><p className="text-sm font-medium">Correo electrónico</p><p className="text-xs text-muted-foreground">{user.email ?? "Añade un correo a tu cuenta"}</p></div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </button>
          <button
            onClick={() => setPasswordOpen(true)}
            className="flex w-full items-center gap-3 border-t border-border px-4 py-3.5 text-left transition-colors hover:bg-secondary"
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

      <Modal open={emailOpen} onClose={() => !savingEmail && setEmailOpen(false)} title="Correo electrónico" description="Usaremos este correo solo como dato de contacto de tu cuenta.">
        <form onSubmit={saveEmail} className="space-y-4"><div className="space-y-1.5"><label htmlFor="profile-email" className="text-sm font-medium">Correo electrónico</label><Input id="profile-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></div><Button type="submit" className="w-full" disabled={savingEmail || !email.trim()}>{savingEmail ? "Guardando…" : "Guardar correo"}</Button></form>
      </Modal>

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
