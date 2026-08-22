"use client"

import Link from "next/link"
import useSWR from "swr"
import { Clapperboard, Film, Play, Star, Tv } from "lucide-react"
import { useAuth } from "@/components/providers/auth-provider"
import { CoverImage } from "@/components/cover-image"
import { PageHeader } from "@/components/page-header"
import { api } from "@/lib/api"
import type { ReplayItem } from "@/lib/api-types"

function label(item: ReplayItem) {
  if (item.type === "Episode") return item.seriesName ? `${item.seriesName} · T${item.season ?? 1} E${item.episode ?? 1}` : "Episodio"
  return item.type === "Series" ? "Serie" : "Película"
}

export default function ReplayPage() {
  const { hasFeature, loading } = useAuth()
  const { data: status } = useSWR(!loading && hasFeature("replay.access") ? "replay:status" : null, () => api.getReplayStatus())
  const { data, error, isLoading } = useSWR<ReplayItem[]>(status?.configured ? "replay:items" : null, () => api.getReplayItems())

  if (!loading && !hasFeature("replay.access")) {
    return <div className="py-16 text-center"><Clapperboard className="mx-auto mb-4 h-10 w-10 text-muted-foreground" /><h1 className="text-xl font-semibold">Replay no está activo</h1><p className="mt-2 text-sm text-muted-foreground">Pide a un administrador que active tu acceso a Replay.</p></div>
  }

  const items = data ?? []
  const movies = items.filter((item) => item.type === "Movie")
  const series = items.filter((item) => item.type === "Series")
  const episodes = items.filter((item) => item.type === "Episode")

  return (
    <div>
      <PageHeader title="Replay" subtitle="Tu biblioteca de cine y series, desde Jellyfin." />
      {!status?.configured && !loading ? (
        <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">Replay está activo para tu cuenta, pero todavía no se ha conectado a Jellyfin.</div>
      ) : error ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-6 text-sm text-destructive">No se pudo cargar la biblioteca de vídeo. Comprueba la conexión de Jellyfin.</div>
      ) : isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">{Array.from({ length: 10 }).map((_, index) => <div key={index} className="skeleton aspect-[2/3] rounded-2xl" />)}</div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">No hay vídeos visibles para el usuario configurado de Jellyfin.</div>
      ) : (
        <div className="space-y-10">
          <ReplayRow title="Películas" icon={Film} items={movies} />
          <ReplayRow title="Series" icon={Tv} items={series} />
          {episodes.length > 0 && <ReplayRow title="Episodios" icon={Play} items={episodes} />}
        </div>
      )}
    </div>
  )
}

function ReplayRow({ title, icon: Icon, items }: { title: string; icon: typeof Film; items: ReplayItem[] }) {
  if (items.length === 0) return null
  return (
    <section>
      <h2 className="mb-4 flex items-center gap-2 text-xl font-semibold"><Icon className="h-5 w-5 text-primary" />{title}</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-7">
        {items.map((item) => <ReplayCard key={item.id} item={item} />)}
      </div>
    </section>
  )
}

function ReplayCard({ item }: { item: ReplayItem }) {
  return (
    <Link href={`/replay/${item.id}`} className="group block">
      <div className="relative"><CoverImage src={item.hasImage ? api.getReplayImageUrl(item.id) : undefined} alt={item.title} className="aspect-[2/3] w-full rounded-2xl" />
        <span className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/30"><span className="flex h-11 w-11 scale-90 items-center justify-center rounded-full bg-primary text-primary-foreground opacity-0 transition-all group-hover:scale-100 group-hover:opacity-100"><Play className="h-5 w-5 translate-x-0.5 fill-current" /></span></span>
      </div>
      <p className="mt-2 truncate text-sm font-medium">{item.title}</p>
      <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">{label(item)} {item.rating ? <><Star className="h-3 w-3 fill-primary text-primary" />{item.rating.toFixed(1)}</> : null}</p>
    </Link>
  )
}
