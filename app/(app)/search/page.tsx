"use client"

import * as React from "react"
import useSWR from "swr"
import { Search as SearchIcon, X } from "lucide-react"
import type { SearchResults, Track } from "@/types/api"
import { api } from "@/lib/api"
import { usePlayer } from "@/components/providers/player-provider"
import { PageHeader } from "@/components/page-header"
import { TrackList, TrackListSkeleton, Section } from "@/components/track-list"
import { MediaCard } from "@/components/media-card"
import { StatusBadge } from "@/components/status-badge"
import { EmptyState } from "@/components/empty-state"
import { cn } from "@/lib/utils"

type Tab = "all" | "tracks" | "albums" | "artists"

const SUGGESTIONS = ["Daft Punk", "Dua Lipa", "The Weeknd", "M83", "MGMT", "Nova Hale"]

export default function SearchPage() {
  const [query, setQuery] = React.useState("")
  const [debounced, setDebounced] = React.useState("")
  const [tab, setTab] = React.useState<Tab>("all")
  const [showAllArtists, setShowAllArtists] = React.useState(false)
  const [showAllAlbums, setShowAllAlbums] = React.useState(false)
  const { playQueue } = usePlayer()

  React.useEffect(() => {
    // External catalogue providers rate-limit searches. Waiting until the user
    // finishes typing avoids issuing requests for every intermediate prefix.
    const id = setTimeout(() => setDebounced(query.trim()), 750)
    return () => clearTimeout(id)
  }, [query])

  React.useEffect(() => {
    setShowAllArtists(false)
    setShowAllAlbums(false)
  }, [debounced])

  const { data, isLoading } = useSWR<SearchResults>(
    debounced ? `search:${debounced}` : null,
    () => api.search(debounced),
  )

  const hasResults =
    data && (data.tracks.length > 0 || data.albums.length > 0 || data.artists.length > 0)

  const showTracks = tab === "all" || tab === "tracks"
  const showAlbums = tab === "all" || tab === "albums"
  const showArtists = tab === "all" || tab === "artists"

  return (
    <div>
      <PageHeader title="Buscar" subtitle="Encuentra canciones, álbumes y artistas de toda la biblioteca." />

      <div className="relative mb-6">
        <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="¿Qué quieres escuchar?"
          className="w-full rounded-2xl border border-border bg-card py-3.5 pl-12 pr-11 text-base outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-ring/40"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            aria-label="Borrar búsqueda"
            className="absolute right-3 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {debounced && (
        <div className="mb-6 flex gap-2 overflow-x-auto no-scrollbar">
          {(["all", "tracks", "albums", "artists"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                tab === t ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:text-foreground",
              )}
            >
              {t === "all" ? "Todo" : t === "tracks" ? "Canciones" : t === "albums" ? "Álbumes" : "Artistas"}
            </button>
          ))}
        </div>
      )}

      {!debounced ? (
        <Section title="Sugerencias">
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setQuery(s)}
                className="rounded-full border border-border bg-card px-4 py-2 text-sm transition-colors hover:border-primary hover:text-primary"
              >
                {s}
              </button>
            ))}
          </div>
        </Section>
      ) : isLoading ? (
        <TrackListSkeleton count={6} />
      ) : !hasResults ? (
        <EmptyState
          icon={SearchIcon}
          title="Sin resultados"
          description={`No encontramos nada para "${debounced}". Prueba con otro término.`}
        />
      ) : (
        <div className="space-y-8">
          {showArtists && (data?.artists.length ?? 0) > 0 && (
            <Section title="Artistas" action={data!.artists.length > 1 ? <button onClick={() => setShowAllArtists((value) => !value)} className="shrink-0 text-sm font-medium text-primary hover:underline">{showAllArtists ? "Mostrar menos" : "Mostrar más"}</button> : undefined}>
              <div className={cn("gap-4", showAllArtists ? "grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6" : "flex overflow-hidden")}>
                {data!.artists.map((a) => (
                  <div key={a.id} className={cn("shrink-0", !showAllArtists && "w-28 sm:w-32 lg:w-36")}><MediaCard title={a.name} subtitle={`${a.albumCount ?? 0} álbumes`} cover={a.image} rounded href={`/artists/${a.id}?name=${encodeURIComponent(a.name)}`} /></div>
                ))}
              </div>
            </Section>
          )}

          {showAlbums && (data?.albums.length ?? 0) > 0 && (
            <Section title="Álbumes" action={data!.albums.length > 1 ? <button onClick={() => setShowAllAlbums((value) => !value)} className="shrink-0 text-sm font-medium text-primary hover:underline">{showAllAlbums ? "Mostrar menos" : "Mostrar más"}</button> : undefined}>
              <div className={cn("gap-4", showAllAlbums ? "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5" : "flex overflow-hidden")}>
                {data!.albums.map((al) => (
                  <div key={al.id} className={cn("relative shrink-0", !showAllAlbums && "w-32 sm:w-36 lg:w-40")}>
                    <MediaCard title={al.title} subtitle={`${al.artist} · ${al.year ?? ""}`} cover={al.cover} href={`/albums/${al.id}?artist=${encodeURIComponent(al.artist)}&title=${encodeURIComponent(al.title)}`} />
                    <div className="absolute left-2 top-2">
                      <StatusBadge status={al.status} />
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {showTracks && (data?.tracks.length ?? 0) > 0 && (
            <Section
              title="Canciones"
              action={
                data!.tracks.some((t) => t.status === "AVAILABLE") ? (
                  <button
                    onClick={() => playQueue(data!.tracks.filter((t) => t.status === "AVAILABLE"))}
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    Reproducir
                  </button>
                ) : undefined
              }
            >
              <TrackList tracks={data!.tracks as Track[]} />
            </Section>
          )}
        </div>
      )}
    </div>
  )
}
