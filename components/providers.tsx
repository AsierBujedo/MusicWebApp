"use client"

import type React from "react"
import { SWRConfig } from "swr"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { ToastProvider } from "@/components/providers/toast-provider"
import { AuthProvider } from "@/components/providers/auth-provider"
import { PlayerProvider } from "@/components/providers/player-provider"
import { RealtimeProvider } from "@/components/providers/realtime-provider"
import { LibraryProvider } from "@/components/providers/library-provider"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig value={{ revalidateOnFocus: false, dedupingInterval: 2000 }}>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <PlayerProvider>
              <LibraryProvider>
                <RealtimeProvider>{children}</RealtimeProvider>
              </LibraryProvider>
            </PlayerProvider>
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </SWRConfig>
  )
}
