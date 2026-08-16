"use client"

import * as React from "react"
import { Eye, EyeOff } from "lucide-react"
import { ApiError } from "@/lib/api-types"
import { api } from "@/lib/api"
import { useToast } from "@/components/providers/toast-provider"
import { Modal } from "@/components/ui/modal"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  autoComplete: string
}) {
  const [show, setShow] = React.useState(false)
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        {label}
      </label>
      <div className="relative">
        <Input
          id={id}
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          className="pr-11"
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          aria-label={show ? "Ocultar contraseña" : "Mostrar contraseña"}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}

export function ChangePasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast()
  const [current, setCurrent] = React.useState("")
  const [next, setNext] = React.useState("")
  const [confirm, setConfirm] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)

  const reset = () => {
    setCurrent("")
    setNext("")
    setConfirm("")
    setError(null)
  }

  const close = () => {
    reset()
    onClose()
  }

  const mismatch = confirm.length > 0 && next !== confirm

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (next.length < 6) {
      setError("La nueva contraseña debe tener al menos 6 caracteres.")
      return
    }
    if (next !== confirm) {
      setError("Las contraseñas no coinciden.")
      return
    }
    setSaving(true)
    try {
      await api.changePassword(current, next)
      toast("Contraseña actualizada correctamente.", "success")
      close()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar la contraseña.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Cambiar contraseña"
      description="Introduce tu contraseña actual y elige una nueva."
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <PasswordField
          id="current-password"
          label="Contraseña actual"
          value={current}
          onChange={setCurrent}
          autoComplete="current-password"
        />
        <PasswordField
          id="new-password"
          label="Nueva contraseña"
          value={next}
          onChange={setNext}
          autoComplete="new-password"
        />
        <div>
          <PasswordField
            id="confirm-password"
            label="Confirmar nueva contraseña"
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
          />
          {mismatch && <p className="mt-1.5 text-xs text-status-failed">Las contraseñas no coinciden.</p>}
        </div>

        {error && (
          <p className={cn("rounded-xl bg-status-failed/10 px-3 py-2 text-sm text-status-failed")} role="alert">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={close} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" disabled={saving || !current || !next || !confirm}>
            {saving && <Spinner className="h-4 w-4" />}
            Guardar
          </Button>
        </div>
      </form>
    </Modal>
  )
}
