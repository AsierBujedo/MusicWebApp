import type {
  AdminStats,
  HistoryEntry,
  MusicRequest,
  Playlist,
  RealtimeEvent,
  SearchResults,
  ServiceHealth,
  Track,
  User,
} from "@/types/api"
import { ApiError, type CreateRequestInput, type CreateUserInput, type MusicApi, type SpotifyImportResult, type SpotifyPlaylist, type SpotifyStatus, type YouTubeCandidate } from "@/lib/api-types"

// Base URL for the backend. In production the app is served behind the same
// origin (`/api/*` -> backend), so an empty base resolves to relative paths.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? ""

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: "include", // rely on HttpOnly session cookie set by backend
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    })
  } catch {
    throw new ApiError("No se pudo conectar. Comprueba tu conexión.", 0)
  }

  if (!res.ok) {
    // Never surface raw technical errors to end users.
    if (res.status === 401) throw new ApiError("Necesitas iniciar sesión.", 401)
    if (res.status === 403) throw new ApiError("No tienes permiso para esto.", 403)
    throw new ApiError("Ha ocurrido un problema. Inténtalo de nuevo.", res.status)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

class RealApi implements MusicApi {
  login(username: string, password: string) {
    return request<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) })
  }
  logout() {
    return request<void>("/api/auth/logout", { method: "POST" })
  }
  getCurrentUser() {
    return request<User>("/api/auth/me")
  }
  changePassword(currentPassword: string, newPassword: string) {
    return request<void>("/api/auth/password", {
      method: "POST",
      body: JSON.stringify({ currentPassword, newPassword }),
    })
  }
  async uploadAvatar(file: File) { const form = new FormData(); form.append("file", file); const res = await fetch(`${BASE}/api/auth/avatar`, {method:"POST", credentials:"include", body:form}); if (!res.ok) throw new ApiError("No se pudo subir la foto", res.status); return res.json() as Promise<User> }
  getSpotifyStatus() {
    return request<SpotifyStatus>("/api/integrations/spotify/status")
  }
  connectSpotify() {
    return request<{ authorizationUrl: string }>("/api/integrations/spotify/connect", { method: "POST" })
  }
  getSpotifyPlaylists() {
    return request<SpotifyPlaylist[]>("/api/integrations/spotify/playlists")
  }
  importSpotifyPlaylists(playlistIds: string[]) {
    return request<SpotifyImportResult>("/api/integrations/spotify/import", { method: "POST", body: JSON.stringify({ playlistIds }) })
  }

  search(query: string) {
    return request<SearchResults>(`/api/search?q=${encodeURIComponent(query)}`)
  }
  getTrack(id: string) {
    return request<Track>(`/api/tracks/${id}`)
  }
  getStreamUrl(id: string) {
    return `${BASE}/api/stream/${id}`
  }

  getRequests() {
    return request<MusicRequest[]>("/api/requests")
  }
  getRequest(id: string) {
    return request<MusicRequest>(`/api/requests/${id}`)
  }
  createRequest(input: CreateRequestInput) {
    return request<MusicRequest>("/api/requests", { method: "POST", body: JSON.stringify(input) })
  }
  deleteRequest(id: string) {
    return request<void>(`/api/requests/${id}`, { method: "DELETE" })
  }
  retryRequest(id: string) {
    return request<MusicRequest>(`/api/requests/${id}/retry`, { method: "POST" })
  }
  cancelRequest(id: string) {
    return request<void>(`/api/requests/${id}/cancel`, { method: "POST" })
  }
  cancelTrackRequest(trackId: string) {
    return request<void>(`/api/requests/track/${trackId}/cancel`, { method: "POST" })
  }
  async uploadRequestAudio(id: string, file: File) {
    const form = new FormData()
    form.append("file", file)
    const res = await fetch(`${BASE}/api/requests/${id}/upload`, { method: "POST", credentials: "include", body: form })
    if (!res.ok) {
      if (res.status === 401) throw new ApiError("Necesitas iniciar sesión.", 401)
      if (res.status === 403) throw new ApiError("No tienes permiso para esto.", 403)
      throw new ApiError("No se pudo importar el archivo de audio.", res.status)
    }
    return res.json() as Promise<MusicRequest>
  }
  getYouTubeCandidates(id: string) {
    return request<YouTubeCandidate[]>(`/api/requests/${id}/youtube-candidates`)
  }
  downloadRequestFromYouTube(id: string, videoId: string) {
    return request<MusicRequest>(`/api/requests/${id}/youtube-download`, { method: "POST", body: JSON.stringify({ videoId }) })
  }

  getFavorites() {
    return request<Track[]>("/api/favorites")
  }
  addFavorite(trackId: string) {
    return request<void>(`/api/favorites/${trackId}`, { method: "POST" })
  }
  removeFavorite(trackId: string) {
    return request<void>(`/api/favorites/${trackId}`, { method: "DELETE" })
  }

  getPlaylists() {
    return request<Playlist[]>("/api/playlists")
  }
  getPlaylist(id: string) {
    return request<Playlist>(`/api/playlists/${id}`)
  }
  createPlaylist(name: string, description?: string, shared = false) {
    return request<Playlist>("/api/playlists", { method: "POST", body: JSON.stringify({ name, description, shared }) })
  }
  updatePlaylist(id: string, patch: Partial<Pick<Playlist, "name" | "description">>) {
    return request<Playlist>(`/api/playlists/${id}`, { method: "PATCH", body: JSON.stringify(patch) })
  }
  deletePlaylist(id: string) {
    return request<void>(`/api/playlists/${id}`, { method: "DELETE" })
  }
  addTrackToPlaylist(id: string, trackId: string) {
    return request<Playlist>(`/api/playlists/${id}/tracks`, { method: "POST", body: JSON.stringify({ trackId }) })
  }
  removeTrackFromPlaylist(id: string, trackId: string) {
    return request<Playlist>(`/api/playlists/${id}/tracks/${trackId}`, { method: "DELETE" })
  }
  reorderPlaylist(id: string, trackIds: string[]) {
    return request<Playlist>(`/api/playlists/${id}/reorder`, { method: "POST", body: JSON.stringify({ trackIds }) })
  }
  addPlaylistCollaborator(id: string, username: string) {
    return request<Playlist>(`/api/playlists/${id}/collaborators`, { method: "POST", body: JSON.stringify({ username }) })
  }
  removePlaylistCollaborator(id: string, username: string) {
    return request<Playlist>(`/api/playlists/${id}/collaborators/${encodeURIComponent(username)}`, { method: "DELETE" })
  }
  resetPlaylistCover(id: string) { return request<Playlist>(`/api/playlists/${id}/cover/reset`, {method:"POST"}) }
  setPlaylistCoverFromTrack(id: string, trackId: string) { return request<Playlist>(`/api/playlists/${id}/cover/from-track/${trackId}`, {method:"POST"}) }
  getArtistCatalog(id: string, name?: string) {
    return request<import("@/types/api").ArtistCatalog>(`/api/catalog/artists/${id}${name ? `?name=${encodeURIComponent(name)}` : ""}`)
  }
  getAlbumCatalog(id: string, artist?: string, title?: string) {
    const query = new URLSearchParams()
    if (artist) query.set("artist", artist)
    if (title) query.set("title", title)
    return request<import("@/types/api").AlbumCatalog>(`/api/catalog/albums/${id}${query.size ? `?${query}` : ""}`)
  }
  requestAlbum(id: string) {
    return request<{ success: boolean; message?: string }>(`/api/catalog/albums/${id}/request`, { method: "POST" })
  }
  requestArtist(id: string) {
    return request<{ success: boolean; requested: number; skipped: number; message?: string }>(`/api/catalog/artists/${id}/request`, { method: "POST" })
  }

  getHistory() {
    return request<HistoryEntry[]>("/api/history")
  }
  recordPlay(trackId: string) {
    return request<void>("/api/history", { method: "POST", body: JSON.stringify({ trackId }) })
  }

  subscribe(handler: (event: RealtimeEvent) => void): () => void {
    if (typeof window === "undefined") return () => {}
    const es = new EventSource(`${BASE}/api/events`, { withCredentials: true })
    es.onmessage = (e) => {
      try {
        handler(JSON.parse(e.data) as RealtimeEvent)
      } catch {
        /* ignore malformed frame */
      }
    }
    es.onerror = () => {
      /* browser auto-reconnects; nothing to surface to the user */
    }
    return () => es.close()
  }

  getStats() {
    return request<AdminStats>("/api/admin/stats")
  }
  getAllTracks() {
    return request<Track[]>("/api/admin/tracks")
  }
  getUsers() {
    return request<User[]>("/api/admin/users")
  }
  createUser(input: CreateUserInput) {
    return request<User>("/api/admin/users", { method: "POST", body: JSON.stringify(input) })
  }
  updateUser(id: string, patch: Partial<User>) {
    return request<User>(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) })
  }
  deleteUser(id: string) {
    return request<void>(`/api/admin/users/${id}`, { method: "DELETE" })
  }
  getAllRequests() {
    return request<MusicRequest[]>("/api/admin/requests")
  }
  setRequestStatus(id: string, status: "APPROVED" | "REJECTED") {
    const action = status === "REJECTED" ? "reject" : "approve"
    return request<MusicRequest>(`/api/admin/requests/${id}/${action}`, { method: "POST" })
  }
  getServices() {
    return request<ServiceHealth[]>("/api/admin/services")
  }
}

export const realApi = new RealApi()
