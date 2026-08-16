"use client"

import * as React from "react"
import { useSWRConfig } from "swr"
import { api } from "@/lib/api"
import { useToast } from "@/components/providers/toast-provider"

// Bridges backend realtime events (SSE in production, in-memory emitter in mock
// mode) into SWR cache revalidation so the UI updates without manual refresh.
export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { mutate } = useSWRConfig()
  const { toast } = useToast()

  React.useEffect(() => {
    const unsubscribe = api.subscribe((event) => {
      if (event.type === "request.updated") {
        mutate("requests")
        mutate("admin:requests")
        mutate(`request:${event.requestId}`)
        mutate("history")
        mutate((key) => typeof key === "string" && key.startsWith("search:"))
        if (event.status === "AVAILABLE") {
          toast("Una de tus solicitudes ya está disponible", "success")
          mutate("admin:stats")
        }
        if (event.status === "FAILED") {
          toast("Una solicitud no se pudo completar", "error")
        }
      }
      if (event.type === "track.updated") {
        mutate((key) => typeof key === "string" && key.startsWith("search:"))
        mutate((key) => typeof key === "string" && key.startsWith("track:"))
      }
    })
    return unsubscribe
  }, [mutate, toast])

  return <>{children}</>
}
