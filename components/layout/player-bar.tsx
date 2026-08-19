"use client"

import * as React from "react"
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Shuffle,
  Repeat,
  Repeat1,
  Volume2,
  VolumeX,
  ChevronDown,
  Heart,
  ListMusic,
} from "lucide-react"
import { usePlayer } from "@/components/providers/player-provider"
import { useLibrary } from "@/components/providers/library-provider"
import { CoverImage } from "@/components/cover-image"
import { cn, formatDuration } from "@/lib/utils"

function ProgressBar({
  value,
  max,
  onSeek,
  className,
}: {
  value: number
  max: number
  onSeek: (v: number) => void
  className?: string
}) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div className={cn("group relative h-1.5 w-full cursor-pointer rounded-full bg-secondary", className)}>
      <input
        type="range"
        min={0}
        max={max || 0}
        value={value}
        onChange={(e) => onSeek(Number(e.target.value))}
        aria-label="Progreso"
        className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
      />
      <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
      <div
        className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-primary opacity-0 shadow transition-opacity group-hover:opacity-100"
        style={{ left: `calc(${pct}% - 6px)` }}
      />
    </div>
  )
}

export function PlayerBar() {
  const {
    currentTrack,
    isPlaying,
    togglePlay,
    next,
    prev,
    position,
    duration,
    seek,
    volume,
    muted,
    setVolume,
    toggleMute,
    repeat,
    cycleRepeat,
    shuffle,
    toggleShuffle,
    expanded,
    setExpanded,
  } = usePlayer()
  const { isFavorite, toggleFavorite } = useLibrary()

  if (!currentTrack) return null
  const fav = isFavorite(currentTrack.id)

  const RepeatIcon = repeat === "one" ? Repeat1 : Repeat

  const Controls = ({ size = "md" }: { size?: "md" | "lg" }) => (
    <div className="flex items-center justify-center gap-2 sm:gap-4">
      <button
        onClick={toggleShuffle}
        aria-label="Aleatorio"
        aria-pressed={shuffle}
        className={cn("transition-colors", shuffle ? "text-primary" : "text-muted-foreground hover:text-foreground")}
      >
        <Shuffle className="h-4 w-4" />
      </button>
      <button onClick={prev} aria-label="Anterior" className="text-foreground hover:text-primary">
        <SkipBack className={cn(size === "lg" ? "h-6 w-6" : "h-5 w-5", "fill-current")} />
      </button>
      <button
        onClick={togglePlay}
        aria-label={isPlaying ? "Pausar" : "Reproducir"}
        className={cn(
          "flex items-center justify-center rounded-full bg-primary text-primary-foreground transition-transform active:scale-95",
          size === "lg" ? "h-14 w-14" : "h-10 w-10",
        )}
      >
        {isPlaying ? (
          <Pause className={cn(size === "lg" ? "h-7 w-7" : "h-5 w-5", "fill-current")} />
        ) : (
          <Play className={cn(size === "lg" ? "h-7 w-7" : "h-5 w-5", "translate-x-0.5 fill-current")} />
        )}
      </button>
      <button onClick={next} aria-label="Siguiente" className="text-foreground hover:text-primary">
        <SkipForward className={cn(size === "lg" ? "h-6 w-6" : "h-5 w-5", "fill-current")} />
      </button>
      <button
        onClick={cycleRepeat}
        aria-label="Repetir"
        aria-pressed={repeat !== "off"}
        className={cn("transition-colors", repeat !== "off" ? "text-primary" : "text-muted-foreground hover:text-foreground")}
      >
        <RepeatIcon className="h-4 w-4" />
      </button>
    </div>
  )

  return (
    <>
      {/* Mini player */}
      <div className="mobile-player-offset fixed inset-x-0 z-40 border-t border-border bg-card/95 backdrop-blur md:left-64">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-3 py-2.5 sm:px-6">
          <button
            onClick={() => setExpanded(true)}
            className="flex min-w-0 flex-1 items-center gap-3 text-left"
            aria-label="Abrir reproductor"
          >
            <CoverImage src={currentTrack.cover} alt={currentTrack.title} className="h-12 w-12 shrink-0" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{currentTrack.title}</p>
              <p className="truncate text-xs text-muted-foreground">{currentTrack.artist}</p>
            </div>
          </button>

          <button
            onClick={() => toggleFavorite(currentTrack)}
            aria-label={fav ? "Quitar de favoritos" : "Añadir a favoritos"}
            className={cn("hidden shrink-0 sm:block", fav ? "text-primary" : "text-muted-foreground hover:text-foreground")}
          >
            <Heart className={cn("h-5 w-5", fav && "fill-current")} />
          </button>

          <div className="hidden flex-1 flex-col items-center gap-1 md:flex">
            <Controls />
            <div className="flex w-full max-w-md items-center gap-2">
              <span className="w-9 text-right text-[10px] tabular-nums text-muted-foreground">
                {formatDuration(position)}
              </span>
              <ProgressBar value={position} max={duration} onSeek={seek} />
              <span className="w-9 text-[10px] tabular-nums text-muted-foreground">{formatDuration(duration)}</span>
            </div>
          </div>

          <div className="hidden items-center gap-2 lg:flex">
            <button onClick={toggleMute} aria-label="Silenciar" className="text-muted-foreground hover:text-foreground">
              {muted || volume === 0 ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
            </button>
            <div className="w-24">
              <ProgressBar value={muted ? 0 : volume * 100} max={100} onSeek={(v) => setVolume(v / 100)} />
            </div>
          </div>

          {/* Mobile play button */}
          <button
            onClick={togglePlay}
            aria-label={isPlaying ? "Pausar" : "Reproducir"}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground md:hidden"
          >
            {isPlaying ? <Pause className="h-5 w-5 fill-current" /> : <Play className="h-5 w-5 translate-x-0.5 fill-current" />}
          </button>
        </div>
        {/* Thin progress on mobile */}
        <div className="px-3 pb-1 md:hidden">
          <ProgressBar value={position} max={duration} onSeek={seek} className="h-1" />
        </div>
      </div>

      {/* Expanded full-screen player */}
      {expanded && (
        <div className="fixed inset-0 z-50 flex flex-col bg-gradient-to-b from-card to-background animate-in">
          <div className="flex items-center justify-between px-5 pb-4 pt-[calc(1rem+env(safe-area-inset-top))]">
            <button onClick={() => setExpanded(false)} aria-label="Cerrar" className="text-muted-foreground hover:text-foreground">
              <ChevronDown className="h-6 w-6" />
            </button>
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Reproduciendo</span>
            <span className="w-6" />
          </div>

          <div className="flex flex-1 flex-col items-center justify-center gap-8 px-6">
            <CoverImage
              src={currentTrack.cover}
              alt={currentTrack.title}
              className="aspect-square w-full max-w-sm shadow-2xl"
            />
            <div className="w-full max-w-md text-center">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0 text-left">
                  <h2 className="truncate text-2xl font-semibold">{currentTrack.title}</h2>
                  <p className="truncate text-muted-foreground">{currentTrack.artist}</p>
                </div>
                <button
                  onClick={() => toggleFavorite(currentTrack)}
                  aria-label={fav ? "Quitar de favoritos" : "Añadir a favoritos"}
                  className={cn("shrink-0", fav ? "text-primary" : "text-muted-foreground hover:text-foreground")}
                >
                  <Heart className={cn("h-7 w-7", fav && "fill-current")} />
                </button>
              </div>
            </div>

            <div className="w-full max-w-md space-y-2">
              <ProgressBar value={position} max={duration} onSeek={seek} />
              <div className="flex justify-between text-xs tabular-nums text-muted-foreground">
                <span>{formatDuration(position)}</span>
                <span>{formatDuration(duration)}</span>
              </div>
            </div>

            <div className="w-full max-w-md">
              <Controls size="lg" />
            </div>

            <div className="flex w-full max-w-md items-center gap-3">
              <button onClick={toggleMute} aria-label="Silenciar" className="text-muted-foreground hover:text-foreground">
                {muted || volume === 0 ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
              </button>
              <ProgressBar value={muted ? 0 : volume * 100} max={100} onSeek={(v) => setVolume(v / 100)} />
              <ListMusic className="h-5 w-5 text-muted-foreground" />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
