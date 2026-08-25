import { Home, Search, Inbox, Heart, ListMusic, Clock, LayoutDashboard, Users, Radio, User, Library, Clapperboard, SlidersHorizontal } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  href: string
  label: string
  icon: LucideIcon
  feature?: string
}

// Primary navigation shown in the desktop sidebar.
export const MAIN_NAV: NavItem[] = [
  { href: "/", label: "Inicio", icon: Home },
  { href: "/search", label: "Buscar", icon: Search },
  { href: "/requests", label: "Solicitudes", icon: Inbox },
  { href: "/favorites", label: "Favoritos", icon: Heart },
  { href: "/playlists", label: "Playlists", icon: ListMusic },
  { href: "/history", label: "Historial", icon: Clock },
  { href: "/replay", label: "Replay", icon: Clapperboard, feature: "replay.access" },
]

// Bottom navigation on mobile (kept to five items for reachability).
export const MOBILE_NAV: NavItem[] = [
  { href: "/", label: "Inicio", icon: Home },
  { href: "/search", label: "Buscar", icon: Search },
  { href: "/requests", label: "Solicitudes", icon: Inbox },
  { href: "/favorites", label: "Favoritos", icon: Heart },
  { href: "/replay", label: "Replay", icon: Clapperboard, feature: "replay.access" },
  { href: "/profile", label: "Perfil", icon: User },
]

// Admin-only navigation.
export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/users", label: "Usuarios", icon: Users, feature: "admin.users" },
  { href: "/admin/features", label: "Funciones", icon: SlidersHorizontal },
  { href: "/admin/tracks", label: "Biblioteca", icon: Library, feature: "admin.library" },
  { href: "/admin/requests", label: "Solicitudes", icon: Inbox, feature: "admin.requests" },
  { href: "/admin/services", label: "Servicios", icon: Radio, feature: "admin.services" },
]
