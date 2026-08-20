"use client"

import { Loader2 } from "lucide-react"
import { useAuth } from "@/components/providers/auth-provider"
import { usePlayer } from "@/components/providers/player-provider"
import { Sidebar } from "@/components/layout/sidebar"
import { MobileNav } from "@/components/layout/mobile-nav"
import { TopBar } from "@/components/layout/top-bar"
import { PlayerBar } from "@/components/layout/player-bar"
import { LoginScreen } from "@/components/auth/login-screen"
import { AccountSetupModal } from "@/components/account-setup-modal"

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const { currentTrack } = usePlayer()

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) return <LoginScreen />

  // Reserve the fixed mobile navigation and, when present, the player bar.
  // Both heights include the iPhone safe-area inset through CSS variables.
  const hasPlayer = Boolean(currentTrack)

  return (
    <div className="flex min-h-dvh bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main
          className={`app-content mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6${hasPlayer ? " app-content-with-player" : ""}`}
        >
          {children}
        </main>
      </div>
      <MobileNav />
      <PlayerBar />
      <AccountSetupModal user={user} />
    </div>
  )
}
