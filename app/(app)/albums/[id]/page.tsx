"use client"

import { useParams, useRouter, useSearchParams } from "next/navigation"
import useSWR from "swr"
import { ArrowLeft, Download, Disc3 } from "lucide-react"
import type { AlbumCatalog } from "@/types/api"
import { api, ApiError } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { CoverImage } from "@/components/cover-image"
import { EmptyState } from "@/components/empty-state"
import { TrackList } from "@/components/track-list"
import { useToast } from "@/components/providers/toast-provider"

export default function AlbumPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const artist = searchParams.get("artist") ?? undefined
  const title = searchParams.get("title") ?? undefined
  const { data, error, isLoading } = useSWR<AlbumCatalog>(id ? `album:${id}:${artist ?? ""}:${title ?? ""}` : null, () => api.getAlbumCatalog(id, artist, title))
  const requestAlbum = async () => {
    if (!data) return
    try { const result = await api.requestAlbum(data.id); toast(result.message ?? "Álbum enviado a descarga", "success") }
    catch (err) { toast(err instanceof ApiError ? err.message : "No se pudo solicitar el álbum", "error") }
  }
  if (error) return <EmptyState icon={Disc3} title="Álbum no encontrado" description="No hemos podido cargar este álbum." action={<Button variant="secondary" onClick={() => router.back()}>Volver</Button>} />
  if (isLoading || !data) return <div className="skeleton h-64 rounded-3xl" />
  return <div>
    <button onClick={() => router.back()} className="mb-5 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />Volver</button>
    <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end"><CoverImage src={data.cover} alt={data.title} className="h-40 w-40 shadow-xl sm:h-52 sm:w-52" /><div className="flex-1"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Álbum</p><h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">{data.title}</h1><p className="mt-1 text-sm text-muted-foreground">{data.artist}{data.year ? ` · ${data.year}` : ""} · {data.tracks.length} canciones</p><Button className="mt-5 gap-2" onClick={requestAlbum} disabled={data.inLibrary}><Download className="h-4 w-4" />{data.inLibrary ? "En biblioteca" : "Solicitar álbum"}</Button></div></div>
    <TrackList tracks={data.tracks} />
  </div>
}
