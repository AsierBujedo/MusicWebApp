"use client"

import * as React from "react"
import useSWR from "swr"
import { Check, Globe2, ShieldAlert, UsersRound } from "lucide-react"
import type { ProductFeatureRollout, ProductFeatureRolloutsResponse } from "@/types/api"
import { api } from "@/lib/api"
import { useAuth } from "@/components/providers/auth-provider"
import { useToast } from "@/components/providers/toast-provider"
import { PageHeader } from "@/components/page-header"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/empty-state"
import { cn } from "@/lib/utils"

function RolloutCard({
  feature,
  users,
  onSave,
}: {
  feature: ProductFeatureRollout
  users: ProductFeatureRolloutsResponse["users"]
  onSave: (mode: ProductFeatureRollout["mode"], usernames: string[]) => Promise<void>
}) {
  const [mode, setMode] = React.useState(feature.mode)
  const [usernames, setUsernames] = React.useState(feature.usernames)
  const [saving, setSaving] = React.useState(false)

  React.useEffect(() => {
    setMode(feature.mode)
    setUsernames(feature.usernames)
  }, [feature.mode, feature.usernames])

  const save = async (nextMode = mode, nextUsernames = usernames) => {
    setSaving(true)
    try {
      await onSave(nextMode, nextUsernames)
    } finally {
      setSaving(false)
    }
  }

  const toggleGlobal = () => {
    const nextMode = mode === "global" ? "off" : "global"
    const nextUsernames = nextMode === "off" ? [] : usernames
    setMode(nextMode)
    setUsernames(nextUsernames)
    void save(nextMode, nextUsernames)
  }

  const toggleUser = (username: string) => {
    setUsernames((current) => current.includes(username) ? current.filter((item) => item !== username) : [...current, username])
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">{feature.label}</h2>
          <p className="mt-1 text-sm text-muted-foreground">Controla quién puede usar esta función de producto.</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={mode === "global"}
          disabled={saving}
          onClick={toggleGlobal}
          className={cn(
            "inline-flex w-full max-w-full items-center justify-between gap-3 self-start rounded-full border px-3 py-2 text-sm font-medium transition-colors disabled:opacity-60 sm:w-auto",
            mode === "global" ? "border-primary/40 bg-primary/10 text-primary" : "border-border bg-secondary text-muted-foreground",
          )}
        >
          <span className="min-w-0 truncate">Activación global</span>
          <span className={cn("relative h-6 w-11 shrink-0 rounded-full transition-colors", mode === "global" ? "bg-primary" : "bg-muted-foreground/35")}>
            <span className={cn("absolute left-1 top-1 h-4 w-4 rounded-full bg-white shadow transition-transform", mode === "global" ? "translate-x-5" : "translate-x-0")} />
          </span>
        </button>
      </div>

      {mode === "global" ? (
        <div className="mt-5 flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm">
          <Globe2 className="h-5 w-5 shrink-0 text-primary" />
          Disponible para todos los usuarios actuales y para los que se creen a partir de ahora.
        </div>
      ) : (
        <div className="mt-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-medium">Friends &amp; Family</p>
              <p className="text-xs text-muted-foreground">Elige uno o varios alias para activarles {feature.label}.</p>
            </div>
            <Button
              size="sm"
              variant={mode === "friends" ? "primary" : "secondary"}
              disabled={saving}
              onClick={() => {
                const nextMode = mode === "friends" ? "off" : "friends"
                setMode(nextMode)
                if (nextMode === "off") void save(nextMode, [])
              }}
            >
              <UsersRound className="h-4 w-4" />
              {mode === "friends" ? "Activo" : "Activar"}
            </Button>
          </div>
          {mode === "friends" ? (
            <>
              <div className="grid gap-2 sm:grid-cols-2">
                {users.map((user) => {
                  const selected = usernames.includes(user.username)
                  return (
                    <button
                      key={user.username}
                      type="button"
                      onClick={() => toggleUser(user.username)}
                      className={cn(
                        "flex items-center gap-3 rounded-xl border p-3 text-left transition-colors",
                        selected ? "border-primary bg-primary/10" : "border-border hover:bg-secondary/60",
                      )}
                    >
                      <Avatar name={user.displayName} src={user.avatar} className="h-9 w-9" />
                      <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{user.displayName}</span><span className="block truncate text-xs text-muted-foreground">@{user.username}</span></span>
                      {selected ? <Check className="h-5 w-5 shrink-0 text-primary" /> : null}
                    </button>
                  )
                })}
              </div>
              {users.length === 0 ? <p className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">Todavía no hay usuarios normales a quienes activar esta función.</p> : null}
              <div className="mt-3 flex justify-end">
                <Button size="sm" disabled={saving} onClick={() => void save("friends", usernames)}>
                  {saving ? "Guardando…" : "Guardar selección"}
                </Button>
              </div>
            </>
          ) : <p className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">La función está desactivada. Activa Friends &amp; Family para seleccionar un grupo reducido.</p>}
        </div>
      )}
    </section>
  )
}

export default function AdminFeaturesPage() {
  const { isAdmin } = useAuth()
  const { toast } = useToast()
  const { data, mutate, isLoading } = useSWR<ProductFeatureRolloutsResponse>(
    isAdmin ? "admin:product-features" : null,
    () => api.getProductFeatureRollouts(),
  )

  if (!isAdmin) {
    return <EmptyState icon={ShieldAlert} title="Solo administradores" description="Las funciones de producto se configuran a nivel global." />
  }

  const save = async (key: string, mode: ProductFeatureRollout["mode"], usernames: string[]) => {
    try {
      await api.setProductFeatureRollout(key, mode, usernames)
      await mutate()
      toast(mode === "global" ? "Función activada globalmente" : mode === "friends" ? "Grupo Friends & Family actualizado" : "Función desactivada", "success")
    } catch {
      toast("No se pudo actualizar la función", "error")
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Funciones" subtitle="Activa funciones de producto para toda la comunidad o solo para Friends & Family." />
      {isLoading ? <div className="space-y-4"><div className="skeleton h-64 rounded-2xl" /></div> : null}
      {data?.features.map((feature) => <RolloutCard key={feature.key} feature={feature} users={data.users} onSave={(mode, usernames) => save(feature.key, mode, usernames)} />)}
    </div>
  )
}
