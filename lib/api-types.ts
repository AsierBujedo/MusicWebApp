import type {
  AdminStats,
  DownloadAvailability,
  ProductFeatureRollout,
  ProductFeatureRolloutsResponse,
  AlbumCatalog,
  ArtistCatalog,
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

export interface YouTubeCandidate {
  videoId: string
  title: string
  channel: string
  duration?: number
}

export interface SpotifyStatus {
  configured: boolean
  connected: boolean
  displayName?: string
}

export interface SpotifyPlaylist {
  id: string
  name: string
  description?: string
  image?: string
  trackCount: number
  ownerName?: string
}

export interface SpotifyImportResult {
  importedPlaylists: number
  importedTracks: number
  matchedTracks: number
  playlists: string[]
}

export interface ReplayItem {
  id: string
  title: string
  type: "Movie" | "Series" | "Episode" | string
  overview?: string
  year?: string
  rating?: number
  runtimeMinutes?: number
  seriesName?: string
  season?: number
  episode?: number
  hasImage: boolean
}

export interface CreateRequestInput {
  type: "track" | "album" | "artist"
  trackId: string
}

export interface CreateUserInput {
  username: string
  displayName: string
  password: string
  email?: string
  role: "ADMIN" | "USER"
  autoApproveRequests?: boolean
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
  changePassword(currentPassword: string, newPassword: string): Promise<void>
  updateProfileEmail(email: string): Promise<User>
  uploadAvatar(file: File): Promise<User>

  // Spotify playlist import
  getSpotifyStatus(): Promise<SpotifyStatus>
  connectSpotify(): Promise<{ authorizationUrl: string }>
  getSpotifyPlaylists(): Promise<SpotifyPlaylist[]>
  importSpotifyPlaylists(playlistIds: string[]): Promise<SpotifyImportResult>

  // Replay / Jellyfin video library
  getReplayStatus(): Promise<{ configured: boolean }>
  getReplayItems(): Promise<ReplayItem[]>
  getReplayItem(id: string): Promise<ReplayItem>
  getReplayImageUrl(id: string): string
  getReplayStreamUrl(id: string): string

  // search + tracks
  search(query: string): Promise<SearchResults>
  searchLocal(query: string): Promise<SearchResults>
  searchExternal(query: string): Promise<SearchResults>
  getTrack(id: string): Promise<Track>
  getStreamUrl(id: string): string

  // requests (current user)
  getRequests(): Promise<MusicRequest[]>
  getRequest(id: string): Promise<MusicRequest>
  getDownloadAvailability(): Promise<DownloadAvailability>
  createRequest(input: CreateRequestInput): Promise<MusicRequest>
  deleteRequest(id: string): Promise<void>
  retryRequest(id: string): Promise<MusicRequest>
  cancelRequest(id: string): Promise<void>
  cancelTrackRequest(trackId: string): Promise<void>
  uploadRequestAudio(id: string, file: File): Promise<MusicRequest>
  getYouTubeCandidates(id: string): Promise<YouTubeCandidate[]>
  downloadRequestFromYouTube(id: string, videoId: string): Promise<MusicRequest>

  // favorites
  getFavorites(): Promise<Track[]>
  addFavorite(trackId: string): Promise<void>
  removeFavorite(trackId: string): Promise<void>

  // playlists
  getPlaylists(): Promise<Playlist[]>
  getPlaylist(id: string): Promise<Playlist>
  createPlaylist(name: string, description?: string, shared?: boolean): Promise<Playlist>
  updatePlaylist(id: string, patch: Partial<Pick<Playlist, "name" | "description">>): Promise<Playlist>
  deletePlaylist(id: string): Promise<void>
  addTrackToPlaylist(id: string, trackId: string): Promise<Playlist>
  removeTrackFromPlaylist(id: string, trackId: string): Promise<Playlist>
  reorderPlaylist(id: string, trackIds: string[]): Promise<Playlist>
  addPlaylistCollaborator(id: string, username: string): Promise<Playlist>
  removePlaylistCollaborator(id: string, username: string): Promise<Playlist>
  setPlaylistCollaboratorReorderPermission(id: string, username: string, canReorder: boolean): Promise<Playlist>
  uploadPlaylistCover(id: string, file: File): Promise<Playlist>
  resetPlaylistCover(id: string): Promise<Playlist>
  setPlaylistFallbackCover(id: string, coverNumber: number): Promise<Playlist>

  // catalogue / full releases
  getArtistCatalog(id: string, name?: string): Promise<ArtistCatalog>
  getArtistCachedTracks(id: string, name: string, query: string): Promise<Track[]>
  getAlbumCatalog(id: string, artist?: string, title?: string): Promise<AlbumCatalog>
  requestAlbum(id: string): Promise<{ success: boolean; message?: string }>
  requestArtist(id: string): Promise<{ success: boolean; requested: number; skipped: number; message?: string }>

  // history
  getHistory(): Promise<HistoryEntry[]>
  recordPlay(trackId: string): Promise<void>

  // realtime
  subscribe(handler: (event: RealtimeEvent) => void): () => void
  syncPlayback(payload: { track: Track; queue: Track[]; isPlaying: boolean; sourceId: string }): Promise<void>

  // admin
  getStats(): Promise<AdminStats>
  getAllTracks(): Promise<Track[]>
  getUsers(): Promise<User[]>
  createUser(input: CreateUserInput): Promise<User>
  updateUser(id: string, patch: Partial<User>): Promise<User>
  deleteUser(id: string): Promise<void>
  updateUserFeatureFlags(id: string, featureFlags: string[]): Promise<User>
  getProductFeatureRollouts(): Promise<ProductFeatureRolloutsResponse>
  setProductFeatureRollout(key: string, mode: ProductFeatureRollout["mode"], usernames: string[]): Promise<ProductFeatureRollout>
  getAllRequests(): Promise<MusicRequest[]>
  setDownloadAvailability(enabled: boolean): Promise<DownloadAvailability>
  setRequestStatus(id: string, status: "APPROVED" | "REJECTED"): Promise<MusicRequest>
  getServices(): Promise<ServiceHealth[]>
  resetSlskd(): Promise<{ success: boolean; cancelled: number; failed: number; restarted: boolean }>
  getDemoUsers(): Promise<User[]>
  startDemo(userId: string): Promise<{ user: User; impersonatedBy: string }>
  exitDemo(): Promise<User>
  getDemoStatus(): Promise<{ active: boolean; adminName?: string }>
}
