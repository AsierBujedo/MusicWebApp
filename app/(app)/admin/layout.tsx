"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ShieldAlert } from "lucide-react"
import { useAuth } from "@/components/providers/auth-provider"
import { ADMIN_NAV } from "@/lib/nav"
import { EmptyState } from "@/components/empty-state"
import { cn } from "@/lib/utils"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading } = useAuth()
  const pathname = usePathname()

  if (loading) return null

  if (!isAdmin) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="Acceso restringido"
        description="Esta zona es solo para administradores."
        action={
          <Link
            href="/"
            className="inline-flex h-10 items-center rounded-full bg-secondary px-5 text-sm font-medium text-secondary-foreground transition-colors hover:bg-accent"
          >
            Volver al inicio
          </Link>
        }
      />
    )
  }

  return (
    <div>
      {/* Admin sub-navigation for mobile / horizontal contexts */}
      <nav className="mb-6 flex gap-2 overflow-x-auto no-scrollbar md:hidden">
        {ADMIN_NAV.map((item) => {
          const active = item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                active ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>
      {children}
    </div>
  )
}
