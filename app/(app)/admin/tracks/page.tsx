"use client"

import useSWR from "swr"
import { Music, Play, Shuffle } from "lucide-react"
import type { Track } from "@/types/api"
import { api } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { PageHeader } from "@/components/page-header"
import { TrackList, TrackListSkeleton } from "@/components/track-list"
import { EmptyState } from "@/components/empty-state"
import { Button } from "@/components/ui/button"

export default function AdminTracksPage() {
  const { data, isLoading } = useSWR<Track[]>("admin:tracks", () => api.getAllTracks())
  const { playQueue, toggleShuffle } = usePlayer()
  const tracks = data ?? []

  return (
    <div>
      <PageHeader
        title="Todas las canciones"
        subtitle={tracks.length > 0 ? `${tracks.length} canciones disponibles en la biblioteca` : undefined}
        action={tracks.length > 0 ? (
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="icon"
              aria-label="Reproducir en aleatorio"
              onClick={() => { toggleShuffle(); playQueue(tracks) }}
            >
              <Shuffle className="h-5 w-5" />
            </Button>
            <Button className="gap-2" onClick={() => playQueue(tracks)}>
              <Play className="h-4 w-4 fill-current" />
              Reproducir todo
            </Button>
          </div>
        ) : undefined}
      />

      {isLoading ? (
        <TrackListSkeleton count={8} />
      ) : tracks.length === 0 ? (
        <EmptyState
          icon={Music}
          title="Biblioteca vacía"
          description="Las canciones disponibles aparecerán aquí cuando Navidrome las indexe."
        />
      ) : (
        <TrackList tracks={tracks} />
      )}
    </div>
  )
}
