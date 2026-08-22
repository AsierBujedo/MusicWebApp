"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import useSWR from "swr"
import { ArrowLeft, Clapperboard, Play, Star } from "lucide-react"
import { CoverImage } from "@/components/cover-image"
import { api } from "@/lib/api"
import type { ReplayItem } from "@/lib/api-types"

export default function ReplayDetailPage() {
  const params = useParams<{ id: string }>()
  const id = params.id
  const { data: item, error, isLoading } = useSWR<ReplayItem>(id ? `replay:item:${id}` : null, () => api.getReplayItem(id))

  if (isLoading) return <div className="skeleton h-[32rem] rounded-2xl" />
  if (error || !item) return <div className="py-16 text-center text-sm text-muted-foreground">No hemos encontrado este vídeo.</div>

  const meta = [item.year, item.runtimeMinutes ? `${item.runtimeMinutes} min` : undefined, item.rating ? `${item.rating.toFixed(1)} / 10` : undefined].filter(Boolean).join(" · ")
  return (
    <div className="mx-auto max-w-6xl">
      <Link href="/replay" className="mb-5 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />Volver a Replay</Link>
      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="aspect-video bg-black">
          <video className="h-full w-full" controls playsInline poster={item.hasImage ? api.getReplayImageUrl(item.id) : undefined} src={api.getReplayStreamUrl(item.id)}>
            Tu navegador no puede reproducir este vídeo.
          </video>
        </div>
        <div className="grid gap-6 p-5 sm:grid-cols-[10rem_1fr] sm:p-7">
          <CoverImage src={item.hasImage ? api.getReplayImageUrl(item.id) : undefined} alt={item.title} className="aspect-[2/3] w-32 rounded-xl sm:w-full" />
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-primary"><Clapperboard className="h-4 w-4" />{item.type === "Series" ? "Serie" : item.type === "Episode" ? "Episodio" : "Película"}</div>
            <h1 className="text-3xl font-semibold tracking-tight">{item.title}</h1>
            {item.seriesName && <p className="mt-1 text-sm text-muted-foreground">{item.seriesName}{item.season ? ` · Temporada ${item.season}, episodio ${item.episode ?? 1}` : ""}</p>}
            {meta && <p className="mt-3 flex items-center gap-1 text-sm text-muted-foreground">{item.rating ? <Star className="h-4 w-4 fill-primary text-primary" /> : null}{meta}</p>}
            <p className="mt-5 max-w-3xl text-sm leading-6 text-muted-foreground">{item.overview || "Sin sinopsis disponible."}</p>
            <a href={api.getReplayStreamUrl(item.id)} className="mt-6 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground"><Play className="h-4 w-4 fill-current" />Reproducir</a>
          </div>
        </div>
      </div>
    </div>
  )
}
