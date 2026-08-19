"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import useSWR, { useSWRConfig } from "swr"
import { ListMusic, Plus } from "lucide-react"
import type { Playlist } from "@/types/api"
import { api } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { useToast } from "@/components/providers/toast-provider"
import { PageHeader } from "@/components/page-header"
import { MediaCard, MediaCardSkeleton } from "@/components/media-card"
import { EmptyState } from "@/components/empty-state"
import { Modal } from "@/components/ui/modal"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { Track } from "@/types/api"

export default function PlaylistsPage() {
  const { data, isLoading } = useSWR<Playlist[]>("playlists", () => api.getPlaylists())
  const { playQueue } = usePlayer()
  const { mutate } = useSWRConfig()
  const { toast } = useToast()
  const router = useRouter()

  const [creating, setCreating] = React.useState(false)
  const [name, setName] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [shared, setShared] = React.useState(false)
  const [saving, setSaving] = React.useState(false)

  const playlists = data ?? []

  const handleCreate = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      const pl = await api.createPlaylist(name.trim(), description.trim() || undefined, shared)
      toast("Playlist creada", "success")
      mutate("playlists")
      setCreating(false)
      setName("")
      setDescription("")
      setShared(false)
      router.push(`/playlists/${pl.id}`)
    } catch {
      toast("No se pudo crear la playlist", "error")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Playlists"
        subtitle="Organiza tu música como más te guste."
        action={
          <Button onClick={() => setCreating(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">Nueva</span>
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <MediaCardSkeleton key={i} />
          ))}
        </div>
      ) : playlists.length === 0 ? (
        <EmptyState
          icon={ListMusic}
          title="Sin playlists"
          description="Crea tu primera playlist para agrupar tus canciones favoritas."
          action={
            <Button onClick={() => setCreating(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Crear playlist
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {playlists.map((pl) => (
            <MediaCard
              key={pl.id}
              title={pl.name}
              subtitle={`by ${pl.ownerUsername ?? "ti"} · ${pl.trackIds.length} canciones`}
              cover={pl.cover}
              href={`/playlists/${pl.id}`}
              onPlay={
                pl.tracks && pl.tracks.some((t) => t.status === "AVAILABLE")
                  ? () => playQueue((pl.tracks as Track[]).filter((t) => t.status === "AVAILABLE"))
                  : undefined
              }
            />
          ))}
        </div>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Nueva playlist">
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="pl-name" className="text-sm font-medium">
              Nombre
            </label>
            <Input
              id="pl-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Mi playlist"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.nativeEvent.isComposing) handleCreate()
              }}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} />
            Playlist compartida
          </label>
          <div className="space-y-1.5">
            <label htmlFor="pl-desc" className="text-sm font-medium">
              Descripción <span className="text-muted-foreground">(opcional)</span>
            </label>
            <Input
              id="pl-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="¿De qué va esta playlist?"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={() => setCreating(false)}>
              Cancelar
            </Button>
            <Button className="flex-1" onClick={handleCreate} disabled={!name.trim() || saving}>
              {saving ? "Creando…" : "Crear"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
