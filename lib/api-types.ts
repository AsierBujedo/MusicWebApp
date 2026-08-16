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

export interface CreateRequestInput {
  type: "track" | "album" | "artist"
  trackId: string
}

export interface CreateUserInput {
  username: string
  displayName: string
  email?: string
  role: "ADMIN" | "USER"
}

// A friendly error the UI can show without leaking technical detail.
export class ApiError extends Error {
  status: number
  constructor(message: string, status = 500) {
    super(message)
    this.status = status
    this.name = "ApiError"
  }
}

export interface MusicApi {
  // auth
  login(username: string, password: string): Promise<User>
  logout(): Promise<void>
  getCurrentUser(): Promise<User>

  // search + tracks
  search(query: string): Promise<SearchResults>
  getTrack(id: string): Promise<Track>
  getStreamUrl(id: string): string

  // requests (current user)
  getRequests(): Promise<MusicRequest[]>
  getRequest(id: string): Promise<MusicRequest>
  createRequest(input: CreateRequestInput): Promise<MusicRequest>
  deleteRequest(id: string): Promise<void>
  retryRequest(id: string): Promise<MusicRequest>

  // favorites
  getFavorites(): Promise<Track[]>
  addFavorite(trackId: string): Promise<void>
  removeFavorite(trackId: string): Promise<void>

  // playlists
  getPlaylists(): Promise<Playlist[]>
  getPlaylist(id: string): Promise<Playlist>
  createPlaylist(name: string, description?: string): Promise<Playlist>
  updatePlaylist(id: string, patch: Partial<Pick<Playlist, "name" | "description">>): Promise<Playlist>
  deletePlaylist(id: string): Promise<void>
  addTrackToPlaylist(id: string, trackId: string): Promise<Playlist>
  removeTrackFromPlaylist(id: string, trackId: string): Promise<Playlist>
  reorderPlaylist(id: string, trackIds: string[]): Promise<Playlist>

  // history
  getHistory(): Promise<HistoryEntry[]>
  recordPlay(trackId: string): Promise<void>

  // realtime
  subscribe(handler: (event: RealtimeEvent) => void): () => void

  // admin
  getStats(): Promise<AdminStats>
  getUsers(): Promise<User[]>
  createUser(input: CreateUserInput): Promise<User>
  updateUser(id: string, patch: Partial<User>): Promise<User>
  deleteUser(id: string): Promise<void>
  getAllRequests(): Promise<MusicRequest[]>
  setRequestStatus(id: string, status: RequestStatus): Promise<MusicRequest>
  getServices(): Promise<ServiceHealth[]>
}
