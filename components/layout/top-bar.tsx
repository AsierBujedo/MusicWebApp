"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { Search, LogOut, User as UserIcon, Sun, Moon, Music } from "lucide-react"
import { useAuth } from "@/components/providers/auth-provider"
import { useTheme } from "@/components/providers/theme-provider"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Dropdown, DropdownItem } from "@/components/ui/dropdown"

export function TopBar() {
  const { user, logout } = useAuth()
  const { theme, toggle: toggleTheme } = useTheme()
  const router = useRouter()

  return (
    <header className="app-header-height sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur sm:px-6">
      {/* Mobile brand */}
      <Link href="/" className="flex items-center gap-2 md:hidden">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Music className="h-4 w-4" />
        </span>
        <span className="font-semibold">Resonar</span>
      </Link>

      <Link
        href="/search"
        className="ml-auto flex items-center gap-2 rounded-full bg-secondary px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent md:ml-0 md:w-full md:max-w-sm"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline">Buscar canciones, artistas…</span>
      </Link>

      <div className="ml-auto flex items-center gap-1">
        <Button variant="ghost" size="icon" aria-label="Cambiar tema" onClick={toggleTheme}>
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>

        {user && (
          <Dropdown
            align="end"
            trigger={
              <button className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <Avatar name={user.displayName} src={user.avatar} className="h-9 w-9" />
              </button>
            }
          >
            <div className="border-b border-border px-3 py-2">
              <p className="truncate text-sm font-medium">{user.displayName}</p>
              <p className="truncate text-xs text-muted-foreground">@{user.username}</p>
            </div>
            <DropdownItem icon={UserIcon} onClick={() => router.push("/profile")}>
              Mi perfil
            </DropdownItem>
            <DropdownItem icon={LogOut} destructive onClick={() => logout()}>
              Cerrar sesión
            </DropdownItem>
          </Dropdown>
        )}
      </div>
    </header>
  )
}
