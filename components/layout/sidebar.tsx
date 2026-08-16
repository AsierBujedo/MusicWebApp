"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Music, Shield } from "lucide-react"
import { MAIN_NAV, ADMIN_NAV } from "@/lib/nav"
import { useAuth } from "@/components/providers/auth-provider"
import { cn } from "@/lib/utils"

export function Sidebar() {
  const pathname = usePathname()
  const { isAdmin } = useAuth()

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/"))

  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:shrink-0 border-r border-border bg-card">
      <div className="flex h-16 items-center gap-2 px-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Music className="h-5 w-5" />
        </span>
        <span className="text-lg font-semibold tracking-tight">Resonar</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2 no-scrollbar">
        {MAIN_NAV.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
              )}
            >
              <Icon className={cn("h-5 w-5 shrink-0", active && "text-primary")} />
              {item.label}
            </Link>
          )
        })}

        {isAdmin && (
          <div className="pt-4">
            <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Administración
            </p>
            {ADMIN_NAV.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                    active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
                  )}
                >
                  <Icon className={cn("h-5 w-5 shrink-0", active && "text-primary")} />
                  {item.label}
                </Link>
              )
            })}
          </div>
        )}
      </nav>

      {isAdmin && (
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2 rounded-xl bg-secondary/40 px-3 py-2 text-xs text-muted-foreground">
            <Shield className="h-4 w-4 text-primary" />
            Modo administrador
          </div>
        </div>
      )}
    </aside>
  )
}
