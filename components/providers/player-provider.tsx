"use client"

import * as React from "react"
import type { HistoryEntry, Track } from "@/types/api"
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
  const mediaControlsRef = React.useRef({
    next: () => {},
    prev: () => {},
  })

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

  const playRandomFromHistory = React.useCallback(async () => {
    try {
      const history = await api.getHistory()
      const seen = new Set<string>()
      const candidates = history
        .map((entry: HistoryEntry) => entry.track)
        .filter((track) => track.status === "AVAILABLE" && !seen.has(track.id) && (seen.add(track.id), true))
      if (candidates.length === 0) return
      const withoutCurrent = candidates.filter((track) => track.id !== currentTrack?.id)
      const pool = withoutCurrent.length > 0 ? withoutCurrent : candidates
      const selected = pool[Math.floor(Math.random() * pool.length)]
      if (selected) start([selected], 0)
    } catch {
      // Lock-screen controls must remain harmless if history is temporarily
      // unavailable (for example during a network transition on iOS).
    }
  }, [currentTrack?.id, start])

  const next = React.useCallback(() => {
    if (queue.length <= 1 && repeat !== "all") {
      void playRandomFromHistory()
      return
    }
    if (!shuffle && repeat !== "all" && index >= queue.length - 1) {
      void playRandomFromHistory()
      return
    }
    setIndex((i) => {
      if (queue.length === 0) return i
      if (shuffle) return Math.floor(Math.random() * queue.length)
      if (i < queue.length - 1) return i + 1
      return repeat === "all" ? 0 : i
    })
    setPosition(0)
  }, [queue.length, index, shuffle, repeat, playRandomFromHistory])

  const prev = React.useCallback(() => {
    if (position > 3) {
      setPosition(0)
      return
    }
    if (queue.length <= 1) {
      void playRandomFromHistory()
      return
    }
    if (index === 0) {
      void playRandomFromHistory()
      return
    }
    setIndex((i) => (i > 0 ? i - 1 : i))
    setPosition(0)
  }, [position, queue.length, index, playRandomFromHistory])

  const togglePlay = React.useCallback(() => {
    if (!currentTrack) return
    setIsPlaying((p) => !p)
  }, [currentTrack])

  const seek = React.useCallback((seconds: number) => {
    const nextPosition = Math.max(0, Math.min(seconds, duration))

    // Updating only React state makes the thumb move briefly, but the audio
    // element continues at its previous timestamp and immediately overwrites it
    // on the next `timeupdate` event.
    if (!MOCK_MODE && audioRef.current) {
      try {
        audioRef.current.currentTime = nextPosition
      } catch {
        // The stream may still be loading. Keep the UI responsive; the next
        // audio event will reconcile its position once it becomes seekable.
      }
    }
    setPosition(nextPosition)
  }, [duration])

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

  // Keep lock-screen handlers current without unregistering and registering
  // them on every audio `timeupdate`. Safari can otherwise lose the previous /
  // next-track actions while the phone is locked.
  React.useEffect(() => {
    mediaControlsRef.current = { next, prev }
  }, [next, prev])

  // Simulated playback clock (mock mode) — advances position while playing.
  // Timestamp-based so that if timers are throttled while the tab is
  // backgrounded or the device is asleep, the position catches up on resume.
  React.useEffect(() => {
    if (!MOCK_MODE || !isPlaying || !currentTrack) return
    let last = Date.now()
    const id = window.setInterval(() => {
      const now = Date.now()
      const delta = (now - last) / 1000
      last = now
      setPosition((p) => {
        const np = p + delta
        if (np >= duration) {
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
        return np
      })
    }, 500)
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

  // --- Background playback / lock-screen controls (MediaSession API) ---
  // Lets audio keep playing and be controlled when the app loses focus, the
  // screen locks, or the PWA is backgrounded (iOS Dynamic Island, Android
  // notification, etc.). Requires real audio (backend stream) to produce sound
  // while locked; metadata/controls are still published in mock mode.

  // Publish the "now playing" metadata shown on the lock screen.
  React.useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return
    if (!currentTrack) {
      navigator.mediaSession.metadata = null
      return
    }
    const rawCover = currentTrack.cover ?? ""
    const cover = rawCover && typeof window !== "undefined" ? new URL(rawCover, window.location.origin).href : rawCover
    navigator.mediaSession.metadata = new MediaMetadata({
      title: currentTrack.title,
      artist: currentTrack.artist,
      album: currentTrack.album ?? "",
      artwork: cover ? [
        { src: cover, sizes: "256x256", type: "image/png" },
        { src: cover, sizes: "512x512", type: "image/png" },
      ] : [],
    })
  }, [currentTrack])

  // Wire hardware / lock-screen control buttons to the player.
  React.useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return
    const ms = navigator.mediaSession
    const handlers: [MediaSessionAction, MediaSessionActionHandler | null][] = [
      ["play", () => setIsPlaying(true)],
      ["pause", () => setIsPlaying(false)],
      ["previoustrack", () => mediaControlsRef.current.prev()],
      ["nexttrack", () => mediaControlsRef.current.next()],
      ["stop", () => setIsPlaying(false)],
    ]
    for (const [action, handler] of handlers) {
      try {
        ms.setActionHandler(action, handler)
      } catch {
        /* action unsupported on this platform */
      }
    }
    return () => {
      for (const [action] of handlers) {
        try {
          ms.setActionHandler(action, null)
        } catch {
          /* ignore */
        }
      }
    }
  }, [])

  // Keep the lock-screen play/pause state in sync.
  React.useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return
    navigator.mediaSession.playbackState = !currentTrack ? "none" : isPlaying ? "playing" : "paused"
  }, [isPlaying, currentTrack])

  // Keep the lock-screen scrubber position accurate.
  React.useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return
    if (typeof navigator.mediaSession.setPositionState !== "function") return
    if (!currentTrack || duration <= 0) return
    try {
      navigator.mediaSession.setPositionState({
        duration,
        position: Math.min(Math.max(position, 0), duration),
        playbackRate: 1,
      })
    } catch {
      /* invalid state (e.g. position > duration mid-transition) */
    }
  }, [position, duration, currentTrack])

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
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          preload="auto"
          // Keeps audio alive in the background instead of forcing fullscreen video UI on iOS.
          playsInline
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
