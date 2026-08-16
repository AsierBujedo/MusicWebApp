"use client"

import * as React from "react"
import type { Track } from "@/types/api"
import { api, MOCK_MODE } from "@/lib/api"

type RepeatMode = "off" | "all" | "one"

interface PlayerContextValue {
  currentTrack: Track | null
  queue: Track[]
  isPlaying: boolean
  position: number
  duration: number
  volume: number
  muted: boolean
  repeat: RepeatMode
  shuffle: boolean
  expanded: boolean
  play: (track: Track, queue?: Track[]) => void
  playQueue: (tracks: Track[], startIndex?: number) => void
  togglePlay: () => void
  next: () => void
  prev: () => void
  seek: (seconds: number) => void
  setVolume: (v: number) => void
  toggleMute: () => void
  cycleRepeat: () => void
  toggleShuffle: () => void
  setExpanded: (v: boolean) => void
}

const PlayerContext = React.createContext<PlayerContextValue | null>(null)

export function PlayerProvider({ children }: { children: React.ReactNode }) {
  const [queue, setQueue] = React.useState<Track[]>([])
  const [index, setIndex] = React.useState(0)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [position, setPosition] = React.useState(0)
  const [volume, setVolumeState] = React.useState(0.8)
  const [muted, setMuted] = React.useState(false)
  const [repeat, setRepeat] = React.useState<RepeatMode>("off")
  const [shuffle, setShuffle] = React.useState(false)
  const [expanded, setExpanded] = React.useState(false)
  const audioRef = React.useRef<HTMLAudioElement | null>(null)

  const currentTrack = queue[index] ?? null
  const duration = currentTrack?.duration ?? 0

  const start = React.useCallback(
    (list: Track[], startIndex: number) => {
      const playable = list.filter((t) => t.status === "AVAILABLE")
      if (playable.length === 0) return
      const target = list[startIndex]
      const finalList = playable
      const finalIndex = Math.max(0, finalList.findIndex((t) => t.id === target?.id))
      setQueue(finalList)
      setIndex(finalIndex === -1 ? 0 : finalIndex)
      setPosition(0)
      setIsPlaying(true)
      const track = finalList[finalIndex === -1 ? 0 : finalIndex]
      if (track) api.recordPlay(track.id).catch(() => {})
    },
    [],
  )

  const play = React.useCallback((track: Track, list?: Track[]) => {
    const source = list ?? [track]
    const startIndex = source.findIndex((t) => t.id === track.id)
    start(source, startIndex === -1 ? 0 : startIndex)
  }, [start])

  const playQueue = React.useCallback((tracks: Track[], startIndex = 0) => start(tracks, startIndex), [start])

  const next = React.useCallback(() => {
    setIndex((i) => {
      if (queue.length === 0) return i
      if (shuffle) return Math.floor(Math.random() * queue.length)
      if (i < queue.length - 1) return i + 1
      return repeat === "all" ? 0 : i
    })
    setPosition(0)
  }, [queue.length, shuffle, repeat])

  const prev = React.useCallback(() => {
    if (position > 3) {
      setPosition(0)
      return
    }
    setIndex((i) => (i > 0 ? i - 1 : i))
    setPosition(0)
  }, [position])

  const togglePlay = React.useCallback(() => {
    if (!currentTrack) return
    setIsPlaying((p) => !p)
  }, [currentTrack])

  const seek = React.useCallback((seconds: number) => setPosition(Math.max(0, Math.min(seconds, duration))), [duration])

  const setVolume = React.useCallback((v: number) => {
    setVolumeState(v)
    setMuted(v === 0)
  }, [])

  const toggleMute = React.useCallback(() => setMuted((m) => !m), [])
  const cycleRepeat = React.useCallback(
    () => setRepeat((r) => (r === "off" ? "all" : r === "all" ? "one" : "off")),
    [],
  )
  const toggleShuffle = React.useCallback(() => setShuffle((s) => !s), [])

  // Simulated playback clock (mock mode) — advances position while playing.
  React.useEffect(() => {
    if (!MOCK_MODE || !isPlaying || !currentTrack) return
    const id = window.setInterval(() => {
      setPosition((p) => {
        if (p + 1 >= duration) {
          if (repeat === "one") return 0
          // schedule advancing to the next track
          window.setTimeout(() => {
            setIndex((i) => {
              if (shuffle) return Math.floor(Math.random() * queue.length)
              if (i < queue.length - 1) return i + 1
              if (repeat === "all") return 0
              setIsPlaying(false)
              return i
            })
          }, 0)
          return 0
        }
        return p + 1
      })
    }, 1000)
    return () => window.clearInterval(id)
  }, [isPlaying, currentTrack, duration, repeat, shuffle, queue.length])

  // Real playback (backend stream) via the <audio> element.
  React.useEffect(() => {
    if (MOCK_MODE) return
    const audio = audioRef.current
    if (!audio || !currentTrack) return
    audio.src = api.getStreamUrl(currentTrack.id)
    audio.volume = muted ? 0 : volume
    if (isPlaying) audio.play().catch(() => setIsPlaying(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTrack?.id])

  React.useEffect(() => {
    if (MOCK_MODE) return
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) audio.play().catch(() => setIsPlaying(false))
    else audio.pause()
  }, [isPlaying])

  React.useEffect(() => {
    if (MOCK_MODE) return
    const audio = audioRef.current
    if (audio) audio.volume = muted ? 0 : volume
  }, [volume, muted])

  const value: PlayerContextValue = {
    currentTrack,
    queue,
    isPlaying,
    position,
    duration,
    volume,
    muted,
    repeat,
    shuffle,
    expanded,
    play,
    playQueue,
    togglePlay,
    next,
    prev,
    seek,
    setVolume,
    toggleMute,
    cycleRepeat,
    toggleShuffle,
    setExpanded,
  }

  return (
    <PlayerContext.Provider value={value}>
      {children}
      {!MOCK_MODE && (
        <audio
          ref={audioRef}
          onTimeUpdate={(e) => setPosition(e.currentTarget.currentTime)}
          onEnded={() => next()}
          className="hidden"
        />
      )}
    </PlayerContext.Provider>
  )
}

export function usePlayer() {
  const ctx = React.useContext(PlayerContext)
  if (!ctx) throw new Error("usePlayer must be used within PlayerProvider")
  return ctx
}
