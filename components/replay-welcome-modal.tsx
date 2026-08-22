"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Clapperboard, Play, Sparkles, Tv } from "lucide-react"
import type { User } from "@/types/api"
import { Modal } from "@/components/ui/modal"
import { Button } from "@/components/ui/button"

export function ReplayWelcomeModal({ user }: { user: User }) {
  const router = useRouter()
  const [open, setOpen] = React.useState(false)
  const revision = user.replayAccessRevision
  const storageKey = `resonar:replay-welcome:${user.id}`

  React.useEffect(() => {
    if (!revision) return
    try {
      setOpen(window.localStorage.getItem(storageKey) !== revision)
    } catch {
      // Private browsing may disable storage; show the welcome rather than
      // silently hiding a newly granted feature.
      setOpen(true)
    }
  }, [revision, storageKey])

  const dismiss = () => {
    try { if (revision) window.localStorage.setItem(storageKey, revision) } catch { /* ignored */ }
    setOpen(false)
  }
  const explore = () => { dismiss(); router.push("/replay") }

  return (
    <Modal open={open} onClose={dismiss} className="max-w-lg overflow-hidden p-0">
      <div className="relative overflow-hidden bg-gradient-to-br from-primary via-orange-500 to-fuchsia-700 px-6 pb-8 pt-10 text-primary-foreground sm:px-9">
        <div className="replay-glow absolute -right-16 -top-16 h-48 w-48 rounded-full bg-white/25" />
        <div className="replay-orbit absolute -bottom-12 -left-12 h-36 w-36 rounded-full border border-white/30" />
        <div className="relative">
          <span className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-black/20 backdrop-blur"><Clapperboard className="h-7 w-7" /></span>
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-white/80">Nuevo en Resonar</p>
          <h2 className="mt-2 font-display text-4xl font-semibold tracking-tight">Bienvenido a Replay</h2>
          <p className="mt-3 max-w-sm text-sm leading-6 text-white/85">Tu cine y tus series, reunidos en una experiencia pensada para tu pantalla grande y tu móvil.</p>
        </div>
      </div>
      <div className="bg-popover p-6 sm:p-8">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl bg-secondary p-4"><Tv className="mb-2 h-5 w-5 text-primary" /><p className="text-sm font-semibold">Tu biblioteca</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Películas, series y episodios desde Jellyfin.</p></div>
          <div className="rounded-2xl bg-secondary p-4"><Sparkles className="mb-2 h-5 w-5 text-primary" /><p className="text-sm font-semibold">Siempre contigo</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Diseñado para navegador, PWA y sofá.</p></div>
        </div>
        <Button className="mt-6 w-full gap-2" onClick={explore}><Play className="h-4 w-4 fill-current" />Explorar Replay</Button>
        <button onClick={dismiss} className="mt-3 w-full text-sm text-muted-foreground hover:text-foreground">Ahora no</button>
      </div>
    </Modal>
  )
}
