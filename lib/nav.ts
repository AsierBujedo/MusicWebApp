import { Home, Search, Inbox, Heart, ListMusic, Clock, LayoutDashboard, Users, Radio, User } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  href: string
  label: string
  icon: LucideIcon
}

// Primary navigation shown in the desktop sidebar.
export const MAIN_NAV: NavItem[] = [
  { href: "/", label: "Inicio", icon: Home },
  { href: "/search", label: "Buscar", icon: Search },
  { href: "/requests", label: "Solicitudes", icon: Inbox },
  { href: "/favorites", label: "Favoritos", icon: Heart },
  { href: "/playlists", label: "Playlists", icon: ListMusic },
  { href: "/history", label: "Historial", icon: Clock },
]

// Bottom navigation on mobile (kept to five items for reachability).
export const MOBILE_NAV: NavItem[] = [
  { href: "/", label: "Inicio", icon: Home },
  { href: "/search", label: "Buscar", icon: Search },
  { href: "/requests", label: "Solicitudes", icon: Inbox },
  { href: "/favorites", label: "Favoritos", icon: Heart },
  { href: "/profile", label: "Perfil", icon: User },
]

// Admin-only navigation.
export const ADMIN_NAV: NavItem[] = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/users", label: "Usuarios", icon: Users },
  { href: "/admin/requests", label: "Solicitudes", icon: Inbox },
  { href: "/admin/services", label: "Servicios", icon: Radio },
]
