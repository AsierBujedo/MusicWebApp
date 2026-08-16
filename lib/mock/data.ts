import type {
  Album,
  Artist,
  HistoryEntry,
  MusicRequest,
  Playlist,
  ServiceHealth,
  Track,
  User,
} from "@/types/api"

// Deterministic cover generator (no external calls). Uses a local SVG endpoint.
export function cover(seed: string): string {
  return `/api/cover?seed=${encodeURIComponent(seed)}`
}

export const MOCK_USERS: User[] = [
  {
    id: "u1",
    username: "asier",
    displayName: "Asier",
    email: "asier@home.local",
    role: "ADMIN",
    active: true,
    avatar: cover("asier-avatar"),
    lastSeen: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
  },
  {
    id: "u2",
    username: "marta",
    displayName: "Marta",
    email: "marta@home.local",
    role: "USER",
    active: true,
    avatar: cover("marta-avatar"),
    lastSeen: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
  },
  {
    id: "u3",
    username: "leo",
    displayName: "Leo",
    email: "leo@home.local",
    role: "USER",
    active: false,
    avatar: cover("leo-avatar"),
    lastSeen: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2).toISOString(),
  },
]

type SeedTrack = Omit<Track, "cover"> & { cover?: string }

function t(track: SeedTrack): Track {
  return { ...track, cover: track.cover ?? cover(`${track.artist}-${track.album ?? track.title}`) }
}

export const MOCK_TRACKS: Track[] = [
  t({ id: "t1", title: "One More Time", artist: "Daft Punk", artistId: "ar1", album: "Discovery", albumId: "al1", year: 2001, duration: 320, status: "AVAILABLE" }),
  t({ id: "t2", title: "Harder, Better, Faster, Stronger", artist: "Daft Punk", artistId: "ar1", album: "Discovery", albumId: "al1", year: 2001, duration: 224, status: "AVAILABLE" }),
  t({ id: "t3", title: "Around the World", artist: "Daft Punk", artistId: "ar1", album: "Homework", albumId: "al2", year: 1997, duration: 429, status: "REQUESTABLE", requestable: true }),
  t({ id: "t4", title: "Get Lucky", artist: "Daft Punk", artistId: "ar1", album: "Random Access Memories", albumId: "al3", year: 2013, duration: 369, status: "DOWNLOADING", progress: 43 }),
  t({ id: "t5", title: "Instant Crush", artist: "Daft Punk", artistId: "ar1", album: "Random Access Memories", albumId: "al3", year: 2013, duration: 337, status: "AVAILABLE" }),
  t({ id: "t6", title: "Houdini", artist: "Dua Lipa", artistId: "ar2", album: "Radical Optimism", albumId: "al4", year: 2024, duration: 186, status: "AVAILABLE" }),
  t({ id: "t7", title: "Levitating", artist: "Dua Lipa", artistId: "ar2", album: "Future Nostalgia", albumId: "al5", year: 2020, duration: 203, status: "AVAILABLE" }),
  t({ id: "t8", title: "Don't Start Now", artist: "Dua Lipa", artistId: "ar2", album: "Future Nostalgia", albumId: "al5", year: 2020, duration: 183, status: "REQUESTABLE", requestable: true }),
  t({ id: "t9", title: "Redbone", artist: "Childish Gambino", artistId: "ar3", album: "Awaken, My Love!", albumId: "al6", year: 2016, duration: 327, status: "AVAILABLE" }),
  t({ id: "t10", title: "This Is America", artist: "Childish Gambino", artistId: "ar3", album: "Singles", albumId: "al7", year: 2018, duration: 225, status: "UNAVAILABLE", requestable: true }),
  t({ id: "t11", title: "Midnight City", artist: "M83", artistId: "ar4", album: "Hurry Up, We're Dreaming", albumId: "al8", year: 2011, duration: 244, status: "AVAILABLE" }),
  t({ id: "t12", title: "Wait", artist: "M83", artistId: "ar4", album: "Hurry Up, We're Dreaming", albumId: "al8", year: 2011, duration: 240, status: "REQUESTABLE", requestable: true }),
  t({ id: "t13", title: "Blinding Lights", artist: "The Weeknd", artistId: "ar5", album: "After Hours", albumId: "al9", year: 2020, duration: 200, status: "AVAILABLE" }),
  t({ id: "t14", title: "Save Your Tears", artist: "The Weeknd", artistId: "ar5", album: "After Hours", albumId: "al9", year: 2020, duration: 215, status: "AVAILABLE" }),
  t({ id: "t15", title: "Starboy", artist: "The Weeknd", artistId: "ar5", album: "Starboy", albumId: "al10", year: 2016, duration: 230, status: "REQUESTABLE", requestable: true }),
  t({ id: "t16", title: "Nightcall", artist: "Kavinsky", artistId: "ar6", album: "OutRun", albumId: "al11", year: 2013, duration: 258, status: "AVAILABLE" }),
  t({ id: "t17", title: "Feel It Still", artist: "Portugal. The Man", artistId: "ar7", album: "Woodstock", albumId: "al12", year: 2017, duration: 163, status: "REQUESTABLE", requestable: true }),
  t({ id: "t18", title: "Electric Feel", artist: "MGMT", artistId: "ar8", album: "Oracular Spectacular", albumId: "al13", year: 2007, duration: 229, status: "AVAILABLE" }),
  t({ id: "t19", title: "Kids", artist: "MGMT", artistId: "ar8", album: "Oracular Spectacular", albumId: "al13", year: 2007, duration: 302, status: "AVAILABLE" }),
  t({ id: "t20", title: "Solar Drift", artist: "Nova Hale", artistId: "ar9", album: "Aurora Rooms", albumId: "al14", year: 2023, duration: 251, status: "AVAILABLE" }),
  t({ id: "t21", title: "Paper Lanterns", artist: "Nova Hale", artistId: "ar9", album: "Aurora Rooms", albumId: "al14", year: 2023, duration: 214, status: "AVAILABLE" }),
  t({ id: "t22", title: "Velvet Hours", artist: "The Marlowes", artistId: "ar10", album: "Late Signals", albumId: "al15", year: 2022, duration: 268, status: "REQUESTABLE", requestable: true }),
]

export const MOCK_ALBUMS: Album[] = [
  { id: "al1", title: "Discovery", artist: "Daft Punk", artistId: "ar1", year: 2001, trackCount: 14, status: "AVAILABLE", cover: cover("Daft Punk-Discovery") },
  { id: "al2", title: "Homework", artist: "Daft Punk", artistId: "ar1", year: 1997, trackCount: 16, status: "REQUESTABLE", cover: cover("Daft Punk-Homework") },
  { id: "al3", title: "Random Access Memories", artist: "Daft Punk", artistId: "ar1", year: 2013, trackCount: 13, status: "AVAILABLE", cover: cover("Daft Punk-Random Access Memories") },
  { id: "al4", title: "Radical Optimism", artist: "Dua Lipa", artistId: "ar2", year: 2024, trackCount: 11, status: "AVAILABLE", cover: cover("Dua Lipa-Radical Optimism") },
  { id: "al5", title: "Future Nostalgia", artist: "Dua Lipa", artistId: "ar2", year: 2020, trackCount: 11, status: "AVAILABLE", cover: cover("Dua Lipa-Future Nostalgia") },
  { id: "al9", title: "After Hours", artist: "The Weeknd", artistId: "ar5", year: 2020, trackCount: 14, status: "AVAILABLE", cover: cover("The Weeknd-After Hours") },
  { id: "al14", title: "Aurora Rooms", artist: "Nova Hale", artistId: "ar9", year: 2023, trackCount: 10, status: "AVAILABLE", cover: cover("Nova Hale-Aurora Rooms") },
]

export const MOCK_ARTISTS: Artist[] = [
  { id: "ar1", name: "Daft Punk", albumCount: 4, image: cover("artist-Daft Punk") },
  { id: "ar2", name: "Dua Lipa", albumCount: 3, image: cover("artist-Dua Lipa") },
  { id: "ar3", name: "Childish Gambino", albumCount: 5, image: cover("artist-Childish Gambino") },
  { id: "ar4", name: "M83", albumCount: 7, image: cover("artist-M83") },
  { id: "ar5", name: "The Weeknd", albumCount: 5, image: cover("artist-The Weeknd") },
  { id: "ar9", name: "Nova Hale", albumCount: 2, image: cover("artist-Nova Hale") },
]

export const MOCK_REQUESTS: MusicRequest[] = [
  {
    id: "r1",
    type: "track",
    trackId: "t3",
    title: "Around the World",
    artist: "Daft Punk",
    cover: cover("Daft Punk-Homework"),
    status: "SEARCHING",
    createdAt: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    requestedBy: "u2",
    requestedByName: "Marta",
  },
  {
    id: "r2",
    type: "track",
    trackId: "t6",
    title: "Houdini",
    artist: "Dua Lipa",
    cover: cover("Dua Lipa-Radical Optimism"),
    status: "AVAILABLE",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
    requestedBy: "u2",
    requestedByName: "Marta",
  },
  {
    id: "r3",
    type: "track",
    trackId: "t10",
    title: "This Is America",
    artist: "Childish Gambino",
    cover: cover("Childish Gambino-Singles"),
    status: "FAILED",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    requestedBy: "u1",
    requestedByName: "Asier",
  },
  {
    id: "r4",
    type: "track",
    trackId: "t4",
    title: "Get Lucky",
    artist: "Daft Punk",
    cover: cover("Daft Punk-Random Access Memories"),
    status: "DOWNLOADING",
    progress: 43,
    createdAt: new Date(Date.now() - 1000 * 60 * 3).toISOString(),
    requestedBy: "u1",
    requestedByName: "Asier",
  },
]

export const MOCK_PLAYLISTS: Playlist[] = [
  {
    id: "p1",
    name: "Para el coche",
    description: "Lo que suena en los viajes en familia.",
    cover: cover("playlist-coche"),
    trackIds: ["t1", "t7", "t13", "t18", "t16"],
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
  },
  {
    id: "p2",
    name: "Concentración",
    description: "Instrumental y tranquilo.",
    cover: cover("playlist-focus"),
    trackIds: ["t20", "t21", "t11"],
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
  },
]

export const MOCK_HISTORY: HistoryEntry[] = [
  { track: MOCK_TRACKS[12], playedAt: new Date(Date.now() - 1000 * 60 * 20).toISOString() },
  { track: MOCK_TRACKS[5], playedAt: new Date(Date.now() - 1000 * 60 * 90).toISOString() },
  { track: MOCK_TRACKS[0], playedAt: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString() },
  { track: MOCK_TRACKS[17], playedAt: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString() },
  { track: MOCK_TRACKS[10], playedAt: new Date(Date.now() - 1000 * 60 * 60 * 30).toISOString() },
]

export const MOCK_FAVORITES: string[] = ["t1", "t6", "t13", "t20"]

export const MOCK_SERVICES: ServiceHealth[] = [
  { name: "DroppedNeedle", key: "droppedneedle", status: "online", detail: "Cola vacía" },
  { name: "Navidrome", key: "navidrome", status: "online", detail: "Biblioteca sincronizada" },
  { name: "slskd", key: "slskd", status: "online", detail: "Conectado" },
]
