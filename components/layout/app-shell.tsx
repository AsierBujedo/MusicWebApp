"use client"

import { Loader2 } from "lucide-react"
import useSWR, { useSWRConfig } from "swr"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/components/providers/auth-provider"
import { usePlayer } from "@/components/providers/player-provider"
import { Sidebar } from "@/components/layout/sidebar"
import { MobileNav } from "@/components/layout/mobile-nav"
import { TopBar } from "@/components/layout/top-bar"
import { PlayerBar } from "@/components/layout/player-bar"
import { LoginScreen } from "@/components/auth/login-screen"
import { AccountSetupModal } from "@/components/account-setup-modal"
import { ReplayWelcomeModal } from "@/components/replay-welcome-modal"

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const { currentTrack } = usePlayer()
  const { mutate } = useSWRConfig()
  const { data: demo } = useSWR(user ? "demo:status" : null, () => api.getDemoStatus())
  const { data: downloadAvailability } = useSWR(user ? "downloads:availability" : null, () => api.getDownloadAvailability())

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
        {demo?.active && <div role="status" style={{ paddingTop: "max(0.5rem, env(safe-area-inset-top))" }} className="sticky top-0 z-50 flex flex-wrap items-center justify-center gap-3 bg-amber-400 px-4 pb-2 text-sm font-semibold text-black shadow-md">Modo demo · estás operando como @{user.username} por cuenta de {demo.adminName}.<Button size="sm" variant="secondary" onClick={() => void api.exitDemo().then(async () => { await mutate("auth:me"); await mutate("demo:status") })}>Volver a mi cuenta</Button></div>}
        {downloadAvailability && !downloadAvailability.enabled && <div role="status" className="relative z-40 border-b border-amber-500/30 bg-amber-400 px-4 py-2 text-center text-sm font-semibold text-black shadow-sm">{downloadAvailability.message ?? "Las descargas de canciones están temporalmente fuera de servicio."}</div>}
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
      <ReplayWelcomeModal user={user} />
    </div>
  )
}
