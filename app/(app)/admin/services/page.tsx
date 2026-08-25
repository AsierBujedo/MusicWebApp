"use client"

import useSWR from "swr"
import * as React from "react"
import { RefreshCw, Server, Activity, RotateCcw, Power } from "lucide-react"
import { api } from "@/lib/api"
import type { DownloadAvailability, ServiceHealth, ServiceStatus } from "@/types/api"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Modal } from "@/components/ui/modal"
import { useToast } from "@/components/providers/toast-provider"
import { useAuth } from "@/components/providers/auth-provider"

const STATUS_META: Record<ServiceStatus, { label: string; dot: string; text: string; ring: string }> = {
  online: {
    label: "Operativo",
    dot: "bg-[var(--color-success)]",
    text: "text-[var(--color-success)]",
    ring: "ring-[var(--color-success)]/30",
  },
  degraded: {
    label: "Degradado",
    dot: "bg-[var(--color-warning)]",
    text: "text-[var(--color-warning)]",
    ring: "ring-[var(--color-warning)]/30",
  },
  offline: {
    label: "Caído",
    dot: "bg-[var(--color-danger)]",
    text: "text-[var(--color-danger)]",
    ring: "ring-[var(--color-danger)]/30",
  },
}

function ServiceRow({ service }: { service: ServiceHealth }) {
  const meta = STATUS_META[service.status]
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4">
      <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-secondary ring-2", meta.ring)}>
        <Server className="h-5 w-5 text-muted-foreground" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{service.name}</p>
        {service.detail ? <p className="truncate text-sm text-muted-foreground">{service.detail}</p> : null}
      </div>
      <div className={cn("flex items-center gap-2 rounded-full bg-secondary px-3 py-1.5", meta.text)}>
        <span className={cn("h-2 w-2 rounded-full", meta.dot)} aria-hidden />
        <span className="text-xs font-medium">{meta.label}</span>
      </div>
    </div>
  )
}

export default function AdminServicesPage() {
  const { isAdmin } = useAuth()
  const { data, isLoading, mutate, isValidating } = useSWR<ServiceHealth[]>("admin:services", () => api.getServices(), {
    refreshInterval: 15000,
  })
  const { data: downloadAvailability, mutate: mutateDownloadAvailability } = useSWR<DownloadAvailability>(
    isAdmin ? "downloads:availability" : null,
    () => api.getDownloadAvailability(),
  )
  const { toast } = useToast()
  const [confirmReset, setConfirmReset] = React.useState(false)
  const [resetting, setResetting] = React.useState(false)
  const [updatingDownloads, setUpdatingDownloads] = React.useState(false)

  const services = data ?? []
  const online = services.filter((s) => s.status === "online").length

  const resetSlskd = async () => {
    setResetting(true)
    try {
      const result = await api.resetSlskd()
      toast(result.restarted ? `slskd reiniciado. ${result.cancelled} descargas canceladas.` : `Cola vaciada (${result.cancelled}), pero faltan o no son válidas las credenciales de administrador de slskd para reiniciarlo.`, result.restarted ? "success" : "info")
      setConfirmReset(false)
      setTimeout(() => void mutate(), 1500)
    } catch {
      toast("No se pudo vaciar o reiniciar slskd", "error")
    } finally {
      setResetting(false)
    }
  }

  const toggleDownloads = async () => {
    const enabled = !(downloadAvailability?.enabled ?? true)
    setUpdatingDownloads(true)
    try {
      await api.setDownloadAvailability(enabled)
      await mutateDownloadAvailability({ enabled }, { revalidate: false })
      toast(
        enabled ? "Las descargas se han reactivado" : "Las descargas están temporalmente fuera de servicio",
        "success",
      )
    } catch {
      toast("No se pudo cambiar el estado de las descargas", "error")
    } finally {
      setUpdatingDownloads(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Servicios"
        description="Estado de los componentes del sistema en tiempo real."
        action={
          <Button variant="secondary" onClick={() => mutate()} disabled={isValidating}>
            <RefreshCw className={cn("h-4 w-4", isValidating && "animate-spin")} aria-hidden />
            Actualizar
          </Button>
        }
      />

      {!isLoading && services.length > 0 ? (
        <div className="flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-sm">
          <Activity className="h-4 w-4 text-[var(--color-success)]" aria-hidden />
          <span className="text-muted-foreground">
            {online} de {services.length} servicios operativos
          </span>
        </div>
      ) : null}

      {isAdmin ? (
        <section className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold">Descargas de canciones</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              {downloadAvailability?.enabled ?? true
                ? "Las solicitudes nuevas se aceptan con normalidad."
                : "Los usuarios ven el aviso de mantenimiento y no pueden solicitar ni reintentar descargas."}
            </p>
          </div>
          <Button
            variant={(downloadAvailability?.enabled ?? true) ? "danger" : "secondary"}
            className="w-full sm:w-auto"
            disabled={updatingDownloads || !downloadAvailability}
            onClick={() => void toggleDownloads()}
          >
            <Power className="h-4 w-4" aria-hidden />
            {updatingDownloads
              ? "Actualizando…"
              : (downloadAvailability?.enabled ?? true)
                ? "Poner en mantenimiento"
                : "Reactivar descargas"}
          </Button>
        </section>
      ) : null}

      <div className="space-y-3">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-20 rounded-2xl" />)
          : services.map((service) => service.key === "slskd" ? (
            <div key={service.key} className="space-y-3">
              <ServiceRow service={service} />
              <Button variant="danger" className="w-full sm:w-auto" onClick={() => setConfirmReset(true)}>
                <RotateCcw className="h-4 w-4" aria-hidden />
                Vaciar cola y reiniciar slskd
              </Button>
            </div>
          ) : <ServiceRow key={service.key} service={service} />)}
      </div>

      <Modal
        open={confirmReset}
        onClose={() => !resetting && setConfirmReset(false)}
        title="¿Vaciar la cola de slskd?"
        description="Se cancelarán todas las descargas de slskd, incluso las que no hayan sido creadas desde Resonar. Después se reiniciará slskd."
      >
        <div className="flex gap-3">
          <Button variant="secondary" className="flex-1" disabled={resetting} onClick={() => setConfirmReset(false)}>Cancelar</Button>
          <Button variant="danger" className="flex-1" disabled={resetting} onClick={() => void resetSlskd()}>{resetting ? "Reiniciando…" : "Vaciar y reiniciar"}</Button>
        </div>
      </Modal>
    </div>
  )
}
