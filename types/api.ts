// Shared API types. The frontend is designed against these contracts and
// never talks to internal services directly — everything goes through the backend.

export type Role = "ADMIN" | "USER"

export interface User {
  id: string
  username: string
  displayName: string
  email?: string
  avatar?: string
  role: Role
  autoApproveRequests?: boolean
  active?: boolean
  lastSeen?: string
}

// Availability status shown on search results / tracks.
export type TrackStatus =
  | "AVAILABLE"
  | "REQUESTABLE"
  | "PENDING"
  | "DOWNLOADING"
  | "UNAVAILABLE"

export interface Track {
  id: string
  title: string
  artist: string
  artistId?: string
  album?: string
  albumId?: string
  cover?: string
  year?: number
  duration?: number // seconds
  status: TrackStatus
  requestable?: boolean
  progress?: number // 0-100 when DOWNLOADING
}

export interface Album {
  id: string
  title: string
  artist: string
  artistId?: string
  cover?: string
  year?: number
  trackCount?: number
  status: TrackStatus
}

export interface Artist {
  id: string
  name: string
  image?: string
  albumCount?: number
}

export type SearchResultType = "track" | "album" | "artist"

export interface SearchResults {
  tracks: Track[]
  albums: Album[]
  artists: Artist[]
}

// Lifecycle of a music request.
export type RequestStatus =
  | "PENDING"
  | "APPROVED"
  | "SEARCHING"
  | "DOWNLOADING"
  | "AVAILABLE"
  | "FAILED"
  | "REJECTED"

export interface MusicRequest {
  id: string
  type: SearchResultType
  trackId: string
  title: string
  artist: string
  cover?: string
  status: RequestStatus
  progress?: number
  errorMessage?: string
  createdAt: string
  requestedBy?: string
  requestedByName?: string
}

export interface Playlist {
  id: string
  name: string
  description?: string
  cover?: string
  trackIds: string[]
  tracks?: Track[]
  createdAt: string
  shared?: boolean
  ownerUsername?: string
  collaboratorUsernames?: string[]
}

export interface HistoryEntry {
  track: Track
  playedAt: string
}

export interface AdminStats {
  users: number
  requests: number
  downloads: number
  availableTracks: number
}

export type ServiceStatus = "online" | "degraded" | "offline"

export interface ServiceHealth {
  name: string
  key: string
  status: ServiceStatus
  detail?: string
}

// Server-Sent Events payloads.
export type RealtimeEvent =
  | {
      type: "request.updated"
      requestId: string
      status: RequestStatus
      progress?: number
    }
  | {
      type: "track.updated"
      trackId: string
      status: TrackStatus
      progress?: number
    }
