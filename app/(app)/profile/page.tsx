"use client"

import useSWR from "swr"
import { LogOut, Heart, ListMusic, Inbox, Shield, Moon, Sun, ChevronRight } from "lucide-react"
import Link from "next/link"
import type { HistoryEntry, Playlist, Track, MusicRequest } from "@/types/api"
import { api } from "@/lib/api"
import { useAuth } from "@/components/providers/auth-provider"
import { useTheme } from "@/components/providers/theme-provider"
import { PageHeader } from "@/components/page-header"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"

export default function ProfilePage() {
  const { user, isAdmin, logout } = useAuth()
  const { theme, toggle } = useTheme()

  const { data: favorites } = useSWR<Track[]>(user ? "favorites" : null, () => api.getFavorites())
  const { data: playlists } = useSWR<Playlist[]>(user ? "playlists" : null, () => api.getPlaylists())
  const { data: requests } = useSWR<MusicRequest[]>(user ? "requests" : null, () => api.getRequests())
  const { data: history } = useSWR<HistoryEntry[]>(user ? "history" : null, () => api.getHistory())

  if (!user) return null

  const stats = [
    { icon: Heart, label: "Favoritos", value: favorites?.length ?? 0, href: "/favorites" },
    { icon: ListMusic, label: "Playlists", value: playlists?.length ?? 0, href: "/playlists" },
    { icon: Inbox, label: "Solicitudes", value: requests?.length ?? 0, href: "/requests" },
  ]

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

      <p className="mt-6 text-center text-xs text-muted-foreground">
        {history?.length ?? 0} reproducciones registradas · Resonar
      </p>
    </div>
  )
}
