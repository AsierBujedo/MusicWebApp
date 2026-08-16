"use client"

import * as React from "react"
import useSWR from "swr"
import type { User } from "@/types/api"
import { api } from "@/lib/api"

interface AuthContextValue {
  user: User | null
  loading: boolean
  isAdmin: boolean
  login: (username: string, password: string) => Promise<User>
  logout: () => Promise<void>
  refresh: () => void
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data, error, isLoading, mutate } = useSWR<User>("auth:me", () => api.getCurrentUser(), {
    shouldRetryOnError: false,
    revalidateOnFocus: false,
  })

  const login = React.useCallback(
    async (username: string, password: string) => {
      const user = await api.login(username, password)
      await mutate(user, { revalidate: false })
      return user
    },
    [mutate],
  )

  const logout = React.useCallback(async () => {
    await api.logout()
    await mutate(undefined, { revalidate: false })
  }, [mutate])

  const user = error ? null : (data ?? null)

  const value: AuthContextValue = {
    user,
    loading: isLoading,
    isAdmin: user?.role === "ADMIN",
    login,
    logout,
    refresh: () => mutate(),
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = React.useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
