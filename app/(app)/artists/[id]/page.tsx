"use client"

import { useParams, useRouter, useSearchParams } from "next/navigation"
import useSWR from "swr"
import * as React from "react"
import { ArrowLeft, Download, Disc3 } from "lucide-react"
import type { ArtistCatalog } from "@/types/api"
import { api, ApiError } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { CoverImage } from "@/components/cover-image"
import { MediaCard } from "@/components/media-card"
import { EmptyState } from "@/components/empty-state"
import { Section } from "@/components/track-list"
import { useToast } from "@/components/providers/toast-provider"

export default function ArtistPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const [showAllReleases, setShowAllReleases] = React.useState(false)
  const name = searchParams.get("name") ?? undefined
  const { data, error, isLoading } = useSWR<ArtistCatalog>(id ? `artist:${id}:${name ?? ""}` : null, () => api.getArtistCatalog(id, name))

  const requestAll = async () => {
    if (!data) return
    try {
      const result = await api.requestArtist(data.id)
      toast(result.requested ? `${result.requested} álbumes/EPs enviados a descarga` : (result.message ?? "No hay discos pendientes"), "success")
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "No se pudo solicitar la discografía", "error")
    }
  }

  if (error) return <EmptyState icon={Disc3} title="Artista no encontrado" description="No hemos podido cargar su discografía." action={<Button variant="secondary" onClick={() => router.back()}>Volver</Button>} />
  if (isLoading || !data) return <div className="space-y-5"><div className="skeleton h-52 rounded-3xl" /><div className="skeleton h-32 rounded-2xl" /></div>
  const releases = [...data.albums, ...data.eps]

  return <div>
    <button onClick={() => router.back()} className="mb-5 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />Volver</button>
    <div className="mb-10 flex flex-col gap-5 sm:flex-row sm:items-end">
      <CoverImage src={data.image} alt={data.name} rounded="rounded-full" className="h-36 w-36 shadow-xl sm:h-48 sm:w-48" />
      <div className="flex-1"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Artista</p><h1 className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">{data.name}</h1><p className="mt-2 text-sm text-muted-foreground">{data.albums.length} álbumes · {data.eps.length} EPs{data.singlesCount ? ` · ${data.singlesCount} singles no incluidos` : ""}</p>
        <Button className="mt-5 gap-2" onClick={requestAll} disabled={!releases.some((release) => !release.inLibrary)}><Download className="h-4 w-4" />Solicitar discografía</Button>
      </div>
    </div>
    <Section title="Álbumes y EPs" subtitle="Los singles, directos y recopilatorios se excluyen de la descarga completa." action={releases.length > 1 ? <button onClick={() => setShowAllReleases((value) => !value)} className="shrink-0 text-sm font-medium text-primary hover:underline">{showAllReleases ? "Mostrar menos" : "Mostrar más"}</button> : undefined}>
      {releases.length ? <div className={showAllReleases ? "grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5" : "flex gap-4 overflow-hidden"}>{releases.map((release) => <div key={release.id} className={showAllReleases ? "" : "w-32 shrink-0 sm:w-36 lg:w-40"}><MediaCard title={release.title} subtitle={`${release.year ?? ""}${release.inLibrary ? " · En biblioteca" : release.requested ? " · Solicitado" : ""}`} cover={release.cover} href={`/albums/${release.id}`} /></div>)}</div> : <EmptyState icon={Disc3} title="Sin álbumes" description="No se han encontrado álbumes o EPs para este artista." />}
    </Section>
  </div>
}
