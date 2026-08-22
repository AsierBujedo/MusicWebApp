"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { MOBILE_NAV } from "@/lib/nav"
import { useAuth } from "@/components/providers/auth-provider"
import { Shield } from "lucide-react"
import { cn } from "@/lib/utils"

export function MobileNav() {
  const pathname = usePathname()
  const { isAdmin, hasFeature } = useAuth()
  const hasAdminPortal = isAdmin || ["admin.users", "admin.requests", "admin.library", "admin.services"].some(hasFeature)
  const mobileItems = MOBILE_NAV.filter((item) => !item.feature || hasFeature(item.feature))
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(href + "/"))

  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 backdrop-blur md:hidden">
      {hasAdminPortal && <Link href="/admin" className="fixed bottom-[calc(4rem+env(safe-area-inset-bottom))] right-4 z-50 flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-lg"><Shield className="h-4 w-4" />Administración</Link>}
      <div className="flex min-h-14 items-stretch justify-around px-1 pb-[env(safe-area-inset-bottom)]">
        {mobileItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-2 text-[10px] font-medium transition-colors",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
