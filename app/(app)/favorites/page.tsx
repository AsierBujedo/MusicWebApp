"use client"

import useSWR from "swr"
import { Heart, Play, Shuffle } from "lucide-react"
import type { Track } from "@/types/api"
import { api } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { PageHeader } from "@/components/page-header"
import { TrackList, TrackListSkeleton } from "@/components/track-list"
import { EmptyState } from "@/components/empty-state"
import { Button } from "@/components/ui/button"

export default function FavoritesPage() {
  const { data, isLoading } = useSWR<Track[]>("favorites", () => api.getFavorites())
  const { playQueue, toggleShuffle } = usePlayer()

  const favorites = data ?? []
  const playable = favorites.filter((t) => t.status === "AVAILABLE")

  return (
    <div>
      <PageHeader
        title="Favoritos"
        subtitle={favorites.length > 0 ? `${favorites.length} canciones que te encantan` : undefined}
        action={
          playable.length > 0 ? (
            <div className="flex gap-2">
              <Button variant="secondary" size="icon" aria-label="Aleatorio" onClick={() => { toggleShuffle(); playQueue(playable) }}>
                <Shuffle className="h-5 w-5" />
              </Button>
              <Button onClick={() => playQueue(playable)} className="gap-2">
                <Play className="h-4 w-4 fill-current" />
                Reproducir
              </Button>
            </div>
          ) : undefined
        }
      />

      {isLoading ? (
        <TrackListSkeleton count={6} />
      ) : favorites.length === 0 ? (
        <EmptyState
          icon={Heart}
          title="Sin favoritos todavía"
          description="Pulsa el corazón en cualquier canción para guardarla aquí."
        />
      ) : (
        <TrackList tracks={favorites} />
      )}
    </div>
  )
}
