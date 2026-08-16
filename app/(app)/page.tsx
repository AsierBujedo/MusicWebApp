"use client"

import Link from "next/link"
import useSWR from "swr"
import { Play, ChevronRight } from "lucide-react"
import type { HistoryEntry, Playlist, Track } from "@/types/api"
import { api } from "@/lib/api"
import { useAuth } from "@/components/providers/auth-provider"
import { usePlayer } from "@/components/providers/player-provider"
import { Section, TrackList, TrackListSkeleton } from "@/components/track-list"
import { MediaCard, MediaCardSkeleton } from "@/components/media-card"
import { CoverImage } from "@/components/cover-image"

function greeting() {
  const h = new Date().getHours()
  if (h < 6) return "Buenas noches"
  if (h < 14) return "Buenos días"
  if (h < 21) return "Buenas tardes"
  return "Buenas noches"
}

export default function HomePage() {
  const { user } = useAuth()
  const { playQueue } = usePlayer()

  const { data: history, isLoading: loadingHistory } = useSWR<HistoryEntry[]>("history", () => api.getHistory())
  const { data: favorites, isLoading: loadingFav } = useSWR<Track[]>("favorites", () => api.getFavorites())
  const { data: playlists, isLoading: loadingPl } = useSWR<Playlist[]>("playlists", () => api.getPlaylists())

  const recentTracks = (history ?? []).map((h) => h.track)
  const quickPicks = recentTracks.filter((t) => t.status === "AVAILABLE").slice(0, 6)

  return (
    <div>
      <div className="mb-8">
        <p className="text-sm text-muted-foreground">{greeting()},</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight">{user?.displayName ?? "hola"}</h1>
      </div>

      {/* Quick picks tiles */}
      {loadingHistory ? (
        <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-16 rounded-2xl" />
          ))}
        </div>
      ) : (
        quickPicks.length > 0 && (
          <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-3">
            {quickPicks.map((track) => (
              <button
                key={track.id}
                onClick={() => playQueue([track])}
                className="group flex items-center gap-3 overflow-hidden rounded-2xl bg-secondary/70 pr-3 text-left transition-colors hover:bg-secondary"
              >
                <CoverImage src={track.cover} alt={track.title} className="h-16 w-16 shrink-0 rounded-none" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{track.title}</span>
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground opacity-0 transition-opacity group-hover:opacity-100">
                  <Play className="h-4 w-4 translate-x-0.5 fill-current" />
                </span>
              </button>
            ))}
          </div>
        )
      )}

      {/* Your playlists */}
      <Section
        title="Tus playlists"
        action={
          <Link href="/playlists" className="flex items-center text-sm text-muted-foreground hover:text-foreground">
            Ver todas <ChevronRight className="h-4 w-4" />
          </Link>
        }
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {loadingPl
            ? Array.from({ length: 5 }).map((_, i) => <MediaCardSkeleton key={i} />)
            : (playlists ?? []).map((pl) => (
                <MediaCard
                  key={pl.id}
                  title={pl.name}
                  subtitle={`${pl.trackIds.length} canciones`}
                  cover={pl.cover}
                  href={`/playlists/${pl.id}`}
                  onPlay={pl.tracks && pl.tracks.length > 0 ? () => playQueue(pl.tracks as Track[]) : undefined}
                />
              ))}
        </div>
      </Section>

      {/* Favorites */}
      <Section
        title="Tus favoritos"
        action={
          <Link href="/favorites" className="flex items-center text-sm text-muted-foreground hover:text-foreground">
            Ver todos <ChevronRight className="h-4 w-4" />
          </Link>
        }
      >
        {loadingFav ? (
          <TrackListSkeleton count={4} />
        ) : (favorites ?? []).length > 0 ? (
          <TrackList tracks={(favorites ?? []).slice(0, 5)} />
        ) : (
          <p className="text-sm text-muted-foreground">Marca canciones con el corazón para verlas aquí.</p>
        )}
      </Section>

      {/* Recently played */}
      <Section title="Escuchado recientemente">
        {loadingHistory ? (
          <TrackListSkeleton count={4} />
        ) : recentTracks.length > 0 ? (
          <TrackList tracks={recentTracks.slice(0, 6)} />
        ) : (
          <p className="text-sm text-muted-foreground">Aún no has escuchado nada. ¡Dale al play!</p>
        )}
      </Section>
    </div>
  )
}
