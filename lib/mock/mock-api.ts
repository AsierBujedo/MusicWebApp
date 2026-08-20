import type {
  AdminStats,
  HistoryEntry,
  MusicRequest,
  Playlist,
  RealtimeEvent,
  RequestStatus,
  SearchResults,
  ServiceHealth,
  Track,
  User,
} from "@/types/api"
import { ApiError, type CreateRequestInput, type CreateUserInput, type MusicApi, type SpotifyImportResult, type SpotifyPlaylist, type SpotifyStatus, type YouTubeCandidate } from "@/lib/api-types"
import {
  cover,
  MOCK_ALBUMS,
  MOCK_ARTISTS,
  MOCK_FAVORITES,
  MOCK_HISTORY,
  MOCK_PLAYLISTS,
  MOCK_REQUESTS,
  MOCK_SERVICES,
  MOCK_TRACKS,
  MOCK_USERS,
} from "@/lib/mock/data"

const SESSION_KEY = "home-music.session"
const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms))

// Progression path for a simulated request lifecycle.
const REQUEST_FLOW: { status: RequestStatus; progress?: number; wait: number }[] = [
  { status: "PENDING", wait: 1200 },
  { status: "SEARCHING", wait: 1800 },
  { status: "DOWNLOADING", progress: 10, wait: 1400 },
  { status: "DOWNLOADING", progress: 45, wait: 1400 },
  { status: "DOWNLOADING", progress: 78, wait: 1400 },
  { status: "DOWNLOADING", progress: 100, wait: 900 },
  { status: "AVAILABLE", wait: 0 },
]

class MockApi implements MusicApi {
  private tracks = new Map(MOCK_TRACKS.map((t) => [t.id, { ...t }]))
  private requests: MusicRequest[] = MOCK_REQUESTS.map((r) => ({ ...r }))
  private playlists: Playlist[] = MOCK_PLAYLISTS.map((p) => ({ ...p }))
  private favorites = new Set(MOCK_FAVORITES)
  private history: HistoryEntry[] = MOCK_HISTORY.map((h) => ({ ...h }))
  private users: User[] = MOCK_USERS.map((u) => ({ ...u }))
  private services: ServiceHealth[] = MOCK_SERVICES.map((s) => ({ ...s }))
  private listeners = new Set<(e: RealtimeEvent) => void>()
  private currentUserId: string | null = null
  // Per-user passwords. Any password logs in initially; once changed here,
  // the new password is enforced so "current password" checks feel real.
  private passwords = new Map<string, string>()

  constructor() {
    if (typeof window !== "undefined") {
      this.currentUserId = window.localStorage.getItem(SESSION_KEY)
    }
    // Keep the pre-seeded in-flight download moving so the UI feels alive.
    this.advanceRequest("r4", 4)
  }

  private emit(event: RealtimeEvent) {
    this.listeners.forEach((l) => l(event))
  }

  private me(): User {
    const user = this.users.find((u) => u.id === this.currentUserId)
    if (!user) throw new ApiError("Necesitas iniciar sesión.", 401)
    return user
  }

  // ---- auth ----
  async login(username: string, password: string): Promise<User> {
    await delay(500)
    const user = this.users.find(
      (u) => u.username.toLowerCase() === username.trim().toLowerCase() || u.email === username.trim().toLowerCase(),
    )
    if (!user || !password) {
      throw new ApiError("Usuario o contraseña incorrectos.", 401)
    }
    // If this user changed their password, enforce it; otherwise any password works.
    const stored = this.passwords.get(user.id)
    if (stored && stored !== password) {
      throw new ApiError("Usuario o contraseña incorrectos.", 401)
    }
    this.currentUserId = user.id
    if (typeof window !== "undefined") window.localStorage.setItem(SESSION_KEY, user.id)
    return { ...user }
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await delay(500)
    const user = this.me()
    const stored = this.passwords.get(user.id)
    if (stored && stored !== currentPassword) {
      throw new ApiError("La contraseña actual no es correcta.", 400)
    }
    if (newPassword.length < 6) {
      throw new ApiError("La nueva contraseña debe tener al menos 6 caracteres.", 400)
    }
    this.passwords.set(user.id, newPassword)
  }
  async uploadAvatar(_file: File): Promise<User> { const user = this.me(); user.avatar = cover(`${user.username}-avatar`); return { ...user } }

  async getSpotifyStatus(): Promise<SpotifyStatus> {
    await delay(150)
    return { configured: false, connected: false }
  }

  async connectSpotify(): Promise<{ authorizationUrl: string }> {
    throw new ApiError("Spotify no está disponible en modo demo.", 400)
  }

  async getSpotifyPlaylists(): Promise<SpotifyPlaylist[]> {
    throw new ApiError("Conecta Spotify primero.", 400)
  }

  async importSpotifyPlaylists(_playlistIds: string[]): Promise<SpotifyImportResult> {
    throw new ApiError("Spotify no está disponible en modo demo.", 400)
  }

  async logout(): Promise<void> {
    await delay(200)
    this.currentUserId = null
    if (typeof window !== "undefined") window.localStorage.removeItem(SESSION_KEY)
  }

  async getCurrentUser(): Promise<User> {
    await delay(200)
    return { ...this.me() }
  }

  // ---- search ----
  async search(query: string): Promise<SearchResults> {
    await delay(450)
    const q = query.trim().toLowerCase()
    if (!q) return { tracks: [], albums: [], artists: [] }
    const match = (s?: string) => (s ?? "").toLowerCase().includes(q)
    return {
      tracks: [...this.tracks.values()].filter((t) => match(t.title) || match(t.artist) || match(t.album)),
      albums: MOCK_ALBUMS.filter((a) => match(a.title) || match(a.artist)),
      artists: MOCK_ARTISTS.filter((a) => match(a.name)),
    }
  }

  async getTrack(id: string): Promise<Track> {
    await delay(150)
    const track = this.tracks.get(id)
    if (!track) throw new ApiError("No encontramos esta canción.", 404)
    return { ...track }
  }

  getStreamUrl(id: string): string {
    // In mock mode we return a bundled short audio loop so playback works offline.
    return `/audio/sample.mp3#${id}`
  }

  // ---- requests ----
  async getRequests(): Promise<MusicRequest[]> {
    await delay(300)
    const me = this.me()
    return this.requests
      .filter((r) => r.requestedBy === me.id)
      .sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt))
      .map((r) => ({ ...r }))
  }

  async getRequest(id: string): Promise<MusicRequest> {
    await delay(150)
    const req = this.requests.find((r) => r.id === id)
    if (!req) throw new ApiError("No encontramos esta solicitud.", 404)
    return { ...req }
  }

  async createRequest(input: CreateRequestInput): Promise<MusicRequest> {
    await delay(400)
    const me = this.me()
    const track = this.tracks.get(input.trackId)
    if (!track) throw new ApiError("No encontramos esta canción.", 404)
    const req: MusicRequest = {
      id: `r${Date.now()}`,
      type: input.type,
      trackId: track.id,
      title: track.title,
      artist: track.artist,
      cover: track.cover,
      status: "PENDING",
      createdAt: new Date().toISOString(),
      requestedBy: me.id,
      requestedByName: me.displayName,
    }
    this.requests.unshift(req)
    track.status = "PENDING"
    this.emit({ type: "track.updated", trackId: track.id, status: "PENDING" })
    this.advanceRequest(req.id, 0)
    return { ...req }
  }

  async deleteRequest(id: string): Promise<void> {
    await delay(200)
    this.requests = this.requests.filter((r) => r.id !== id)
  }

  async retryRequest(id: string): Promise<MusicRequest> {
    await delay(300)
    const me = this.me()
    const req = this.requests.find((r) => r.id === id)
    if (!req) throw new ApiError("No encontramos esta solicitud.", 404)
    const autoApprover = me.role === "ADMIN" || Boolean(me.autoApproveRequests)
    req.status = autoApprover && req.status === "FAILED" ? "APPROVED" : "PENDING"
    req.progress = undefined
    this.advanceRequest(req.id, 0)
    return { ...req }
  }

  async cancelRequest(id: string): Promise<void> {
    await delay(200)
    this.requests = this.requests.filter((request) => request.id !== id)
  }

  async cancelTrackRequest(trackId: string): Promise<void> {
    await delay(200)
    const me = this.me()
    const request = this.requests.find(
      (item) =>
        item.trackId === trackId &&
        ["APPROVED", "SEARCHING", "DOWNLOADING"].includes(item.status) &&
        (me.role === "ADMIN" || item.requestedBy === me.id),
    )
    if (!request) throw new ApiError("No encontramos una descarga activa.", 404)
    await this.cancelRequest(request.id)
  }

  async uploadRequestAudio(id: string, _file: File): Promise<MusicRequest> {
    await delay(300)
    const req = this.requests.find((r) => r.id === id)
    if (!req) throw new ApiError("No encontramos esta solicitud.", 404)
    req.status = "AVAILABLE"
    req.progress = undefined
    const track = this.tracks.get(req.trackId)
    if (track) {
      track.status = "AVAILABLE"
      track.progress = undefined
      this.emit({ type: "track.updated", trackId: track.id, status: track.status })
    }
    this.emit({ type: "request.updated", requestId: id, status: req.status })
    return { ...req }
  }

  async getYouTubeCandidates(_id: string): Promise<YouTubeCandidate[]> {
    await delay(300)
    return [
      { videoId: "dQw4w9WgXcQ", title: "Resultado oficial", channel: "Canal oficial", duration: 213 },
      { videoId: "3JZ_D3ELwOQ", title: "Resultado alternativo", channel: "Music channel", duration: 218 },
    ]
  }

  async downloadRequestFromYouTube(id: string, _videoId: string): Promise<MusicRequest> {
    return this.uploadRequestAudio(id, new File([], "audio.mp3", { type: "audio/mpeg" }))
  }

  // Walk a request through its lifecycle emitting realtime events.
  private advanceRequest(id: string, startStep: number) {
    let step = startStep
    const tick = () => {
      const req = this.requests.find((r) => r.id === id)
      if (!req || step >= REQUEST_FLOW.length) return
      const phase = REQUEST_FLOW[step]
      req.status = phase.status
      req.progress = phase.progress
      this.emit({ type: "request.updated", requestId: id, status: phase.status, progress: phase.progress })

      const track = this.tracks.get(req.trackId)
      if (track) {
        if (phase.status === "DOWNLOADING") {
          track.status = "DOWNLOADING"
          track.progress = phase.progress
        } else if (phase.status === "AVAILABLE") {
          track.status = "AVAILABLE"
          track.progress = undefined
        }
        this.emit({ type: "track.updated", trackId: track.id, status: track.status, progress: track.progress })
      }

      if (phase.status === "AVAILABLE") return
      step += 1
      setTimeout(tick, phase.wait)
    }
    setTimeout(tick, REQUEST_FLOW[startStep]?.wait ?? 800)
  }

  // ---- favorites ----
  async getFavorites(): Promise<Track[]> {
    await delay(250)
    return [...this.favorites].map((id) => this.tracks.get(id)).filter((t): t is Track => Boolean(t)).map((t) => ({ ...t }))
  }

  async addFavorite(trackId: string): Promise<void> {
    await delay(120)
    this.favorites.add(trackId)
  }

  async removeFavorite(trackId: string): Promise<void> {
    await delay(120)
    this.favorites.delete(trackId)
  }

  // ---- playlists ----
  private hydrate(p: Playlist): Playlist {
    return {
      ...p,
      tracks: p.trackIds.map((id) => this.tracks.get(id)).filter((t): t is Track => Boolean(t)).map((t) => ({ ...t })),
    }
  }

  async getPlaylists(): Promise<Playlist[]> {
    await delay(300)
    return this.playlists.map((p) => this.hydrate(p))
  }

  async getPlaylist(id: string): Promise<Playlist> {
    await delay(200)
    const p = this.playlists.find((p) => p.id === id)
    if (!p) throw new ApiError("No encontramos esta playlist.", 404)
    return this.hydrate(p)
  }

  async createPlaylist(name: string, description?: string, shared = false): Promise<Playlist> {
    await delay(300)
    const p: Playlist = {
      id: `p${Date.now()}`,
      name: name.trim() || "Nueva playlist",
      description,
      cover: cover(`playlist-${name}-${Date.now()}`),
      trackIds: [],
      createdAt: new Date().toISOString(),
      shared,
    }
    this.playlists.unshift(p)
    return this.hydrate(p)
  }

  async updatePlaylist(id: string, patch: Partial<Pick<Playlist, "name" | "description">>): Promise<Playlist> {
    await delay(200)
    const p = this.playlists.find((p) => p.id === id)
    if (!p) throw new ApiError("No encontramos esta playlist.", 404)
    Object.assign(p, patch)
    return this.hydrate(p)
  }

  async deletePlaylist(id: string): Promise<void> {
    await delay(200)
    this.playlists = this.playlists.filter((p) => p.id !== id)
  }

  async addTrackToPlaylist(id: string, trackId: string): Promise<Playlist> {
    await delay(200)
    const p = this.playlists.find((p) => p.id === id)
    if (!p) throw new ApiError("No encontramos esta playlist.", 404)
    if (!p.trackIds.includes(trackId)) p.trackIds.push(trackId)
    return this.hydrate(p)
  }

  async removeTrackFromPlaylist(id: string, trackId: string): Promise<Playlist> {
    await delay(200)
    const p = this.playlists.find((p) => p.id === id)
    if (!p) throw new ApiError("No encontramos esta playlist.", 404)
    p.trackIds = p.trackIds.filter((t) => t !== trackId)
    return this.hydrate(p)
  }

  async reorderPlaylist(id: string, trackIds: string[]): Promise<Playlist> {
    await delay(150)
    const p = this.playlists.find((p) => p.id === id)
    if (!p) throw new ApiError("No encontramos esta playlist.", 404)
    p.trackIds = trackIds
    return this.hydrate(p)
  }
  async addPlaylistCollaborator(id: string, username: string): Promise<Playlist> {
    const playlist = await this.getPlaylist(id)
    playlist.shared = true
    playlist.collaboratorUsernames = [...(playlist.collaboratorUsernames ?? []), username]
    return playlist
  }
  async removePlaylistCollaborator(id: string, username: string): Promise<Playlist> {
    const playlist = await this.getPlaylist(id)
    playlist.collaboratorUsernames = (playlist.collaboratorUsernames ?? []).filter((name) => name !== username)
    return playlist
  }
  async resetPlaylistCover(id: string): Promise<Playlist> { const p = this.playlists.find((item) => item.id === id); if (!p) throw new ApiError("Playlist no encontrada",404); p.cover = undefined; return {...p} }
  async setPlaylistCoverFromTrack(id: string, trackId: string): Promise<Playlist> { const p = this.playlists.find((item) => item.id === id); const track=this.tracks.get(trackId); if(!p||!track?.cover) throw new ApiError("Portada no encontrada",404); p.cover=track.cover; return {...p} }
  async getArtistCatalog(id: string, name?: string): Promise<import("@/types/api").ArtistCatalog> {
    const tracks = [...this.tracks.values()].filter((track) => track.artistId === id || track.artist === name)
    const first = tracks[0]
    if (!first) throw new ApiError("No encontramos este artista.", 404)
    const albums = [...new Map(tracks.filter((track) => track.albumId).map((track) => [track.albumId!, { id: track.albumId!, title: track.album ?? "Álbum", year: track.year, cover: track.cover, inLibrary: track.status === "AVAILABLE", requested: track.status === "PENDING" }])).values()]
    return { id, name: first.artist, albums, eps: [], singlesCount: 0 }
  }
  async getAlbumCatalog(id: string, artist?: string, title?: string): Promise<import("@/types/api").AlbumCatalog> {
    const tracks = [...this.tracks.values()].filter((track) => track.albumId === id || (track.artist === artist && track.album === title))
    const first = tracks[0]
    if (!first) throw new ApiError("No encontramos este álbum.", 404)
    return { id, title: first.album ?? "Álbum", artist: first.artist, artistId: first.artistId, year: first.year, cover: first.cover, inLibrary: tracks.every((track) => track.status === "AVAILABLE"), tracks }
  }
  async requestAlbum(_id: string): Promise<{ success: boolean; message?: string }> {
    return { success: true, message: "Solicitud enviada" }
  }
  async requestArtist(_id: string): Promise<{ success: boolean; requested: number; skipped: number; message?: string }> {
    return { success: true, requested: 1, skipped: 0, message: "Discografía enviada" }
  }

  // ---- history ----
  async getHistory(): Promise<HistoryEntry[]> {
    await delay(250)
    return this.history.map((h) => ({ ...h }))
  }

  async recordPlay(trackId: string): Promise<void> {
    const track = this.tracks.get(trackId)
    if (!track) return
    this.history = [{ track: { ...track }, playedAt: new Date().toISOString() }, ...this.history.filter((h) => h.track.id !== trackId)].slice(0, 50)
  }

  // ---- realtime ----
  subscribe(handler: (event: RealtimeEvent) => void): () => void {
    this.listeners.add(handler)
    return () => this.listeners.delete(handler)
  }

  // ---- admin ----
  async getStats(): Promise<AdminStats> {
    await delay(300)
    return {
      users: this.users.length,
      requests: this.requests.length,
      downloads: this.requests.filter((r) => r.status === "DOWNLOADING").length,
      availableTracks: [...this.tracks.values()].filter((t) => t.status === "AVAILABLE").length,
    }
  }

  async getAllTracks(): Promise<Track[]> {
    await delay(300)
    return [...this.tracks.values()]
      .filter((track) => track.status === "AVAILABLE")
      .sort((a, b) => `${a.artist}\u0000${a.album ?? ""}\u0000${a.title}`.localeCompare(`${b.artist}\u0000${b.album ?? ""}\u0000${b.title}`))
      .map((track) => ({ ...track }))
  }

  async getUsers(): Promise<User[]> {
    await delay(300)
    return this.users.map((u) => ({ ...u }))
  }

  async createUser(input: CreateUserInput): Promise<User> {
    await delay(300)
    const user: User = {
      id: `u${Date.now()}`,
      username: input.username,
      displayName: input.displayName,
      email: input.email,
      role: input.role,
      autoApproveRequests: input.role === "USER" && input.autoApproveRequests,
      active: true,
      avatar: cover(`${input.username}-avatar`),
      lastSeen: new Date().toISOString(),
    }
    this.users.push(user)
    return { ...user }
  }

  async updateUser(id: string, patch: Partial<User>): Promise<User> {
    await delay(200)
    const user = this.users.find((u) => u.id === id)
    if (!user) throw new ApiError("No encontramos este usuario.", 404)
    Object.assign(user, patch)
    return { ...user }
  }

  async deleteUser(id: string): Promise<void> {
    await delay(200)
    this.users = this.users.filter((u) => u.id !== id)
  }

  async getAllRequests(): Promise<MusicRequest[]> {
    await delay(300)
    return this.requests
      .slice()
      .sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt))
      .map((r) => ({ ...r }))
  }

  async setRequestStatus(id: string, status: "APPROVED" | "REJECTED"): Promise<MusicRequest> {
    await delay(250)
    const req = this.requests.find((r) => r.id === id)
    if (!req) throw new ApiError("No encontramos esta solicitud.", 404)
    req.status = status
    if (status === "APPROVED") this.advanceRequest(req.id, 2)
    this.emit({ type: "request.updated", requestId: id, status, progress: req.progress })
    return { ...req }
  }

  async getServices(): Promise<ServiceHealth[]> {
    await delay(300)
    return this.services.map((s) => ({ ...s }))
  }
}

export const mockApi = new MockApi()
