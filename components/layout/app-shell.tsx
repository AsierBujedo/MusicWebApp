"use client"

import { Loader2 } from "lucide-react"
import { useAuth } from "@/components/providers/auth-provider"
import { usePlayer } from "@/components/providers/player-provider"
import { Sidebar } from "@/components/layout/sidebar"
import { MobileNav } from "@/components/layout/mobile-nav"
import { TopBar } from "@/components/layout/top-bar"
import { PlayerBar } from "@/components/layout/player-bar"
import { LoginScreen } from "@/components/auth/login-screen"

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

  // Bottom padding reserves space for the mobile nav (57px) and the player bar when active.
  const hasPlayer = Boolean(currentTrack)

  return (
    <div className="flex min-h-dvh bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main
          className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6"
          style={{ paddingBottom: hasPlayer ? "170px" : "80px" }}
        >
          {children}
        </main>
      </div>
      <MobileNav />
      <PlayerBar />
    </div>
  )
}
