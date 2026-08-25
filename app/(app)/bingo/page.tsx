"use client"

import * as React from "react"
import useSWR from "swr"
import { Copy, Play, QrCode, Sparkles, Trophy } from "lucide-react"
import { api } from "@/lib/api"
import type { Playlist } from "@/types/api"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/providers/toast-provider"
import { usePlayer } from "@/components/providers/player-provider"

const call = async (path: string, init?: RequestInit) => {
  const res = await fetch(path, { credentials: "include", headers: { "Content-Type": "application/json" }, ...init })
  if (!res.ok) throw new Error()
  return res.json()
}

export default function BingoPage() {
  const { toast } = useToast()
  const { play } = usePlayer()
  const { data: playlists } = useSWR<Playlist[]>("playlists", () => api.getPlaylists())
  const { data: games, mutate } = useSWR("bingo:games", () => call("/api/bingo/games"), { refreshInterval: 3000 })
  const [playlistId, setPlaylistId] = React.useState("")
  const [size, setSize] = React.useState(4)
  const [creating, setCreating] = React.useState(false)
  const create = async () => { try { setCreating(true); await call("/api/bingo/games", { method: "POST", body: JSON.stringify({ playlistId, gridSize: size }) }); await mutate(); toast("Partida creada", "success") } catch { toast("Elige una playlist con suficientes canciones", "error") } finally { setCreating(false) } }
  const copy = async (code: string) => { await navigator.clipboard.writeText(`${location.origin}/bingo/${code}`); toast("Enlace copiado", "success") }
  return <div className="space-y-6"><PageHeader title="Bingo musical" subtitle="Crea una partida, comparte el código y deja que la música decida." />
    <section className="overflow-hidden rounded-3xl border border-primary/25 bg-[radial-gradient(circle_at_top_right,rgba(255,108,83,.28),transparent_45%),var(--color-card)] p-6"><div className="flex items-start gap-4"><Sparkles className="h-7 w-7 text-primary" /><div><h2 className="text-xl font-semibold">Nueva partida</h2><p className="mt-1 text-sm text-muted-foreground">Cada participante recibe un cartón diferente y verificable.</p></div></div><div className="mt-5 grid gap-3 sm:grid-cols-3"><select value={playlistId} onChange={(e) => setPlaylistId(e.target.value)} className="h-10 rounded-xl border border-border bg-background px-3 text-sm"><option value="">Elige una playlist</option>{(playlists ?? []).map((p) => <option key={p.id} value={p.id}>{p.name} · {p.trackIds.length} canciones</option>)}</select><select value={size} onChange={(e) => setSize(Number(e.target.value))} className="h-10 rounded-xl border border-border bg-background px-3 text-sm"><option value={3}>Cartón 3 × 3</option><option value={4}>Cartón 4 × 4</option><option value={5}>Cartón 5 × 5</option></select><Button disabled={!playlistId || creating} onClick={() => void create()}><Trophy className="h-4 w-4" />{creating ? "Creando…" : "Crear partida"}</Button></div></section>
    <section className="space-y-3">{(games ?? []).map((game: any) => <div key={game.id} className="rounded-2xl border border-border bg-card p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-semibold">{game.title}</p><p className="text-sm text-muted-foreground">{game.players?.length ?? 0} jugadores · {game.status === "LOBBY" ? "Esperando" : game.status}</p></div><div className="flex gap-2"><Button size="sm" variant="secondary" onClick={() => void copy(game.code)}><Copy className="h-4 w-4" />Invitar</Button>{game.status === "LOBBY" && <Button size="sm" onClick={async () => { const state = await call(`/api/bingo/games/${game.id}/start`, { method: "POST" }); if (state.currentTrack) play(state.currentTrack); mutate() }}><Play className="h-4 w-4" />Empezar</Button>}{game.status === "RUNNING" && <Button size="sm" onClick={async () => { const state = await call(`/api/bingo/games/${game.id}/next`, { method: "POST" }); if (state.currentTrack) play(state.currentTrack); mutate() }}>Siguiente</Button>}</div></div><div className="mt-3 flex items-center gap-3"><img src={`/api/bingo/public/${game.code}/qr`} alt={`QR para ${game.title}`} className="h-20 w-20 rounded-lg bg-white p-1" /><p className="flex items-center gap-2 text-xs text-muted-foreground"><QrCode className="h-4 w-4" />Código: {game.code}<br />{location.origin}/bingo/{game.code}</p></div>{game.claims?.map((claim: any) => <div key={claim.id} className="mt-3 flex items-center justify-between rounded-xl bg-secondary p-3 text-sm"><span>{game.players?.find((p: any) => p.id === claim.playerId)?.name ?? "Jugador"} reclama {claim.kind === "BINGO" ? "BINGO" : "línea"}</span><span className="flex gap-2"><Button size="sm" variant="secondary" onClick={async () => { await call(`/api/bingo/games/${game.id}/claims/${claim.id}`, { method: "POST", body: JSON.stringify({ approved: false }) }); mutate() }}>Rechazar</Button><Button size="sm" onClick={async () => { await call(`/api/bingo/games/${game.id}/claims/${claim.id}`, { method: "POST", body: JSON.stringify({ approved: true }) }); mutate() }}>Aprobar</Button></span></div>)}</div>)}{games?.length === 0 && <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">Todavía no has creado ninguna partida.</p>}</section></div>
}
