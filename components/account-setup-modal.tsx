"use client"

import * as React from "react"
import type { User } from "@/types/api"
import { api } from "@/lib/api"
import { ApiError } from "@/lib/api-types"
import { Modal } from "@/components/ui/modal"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"

export function AccountSetupModal({ user, onComplete }: { user: User; onComplete: () => void }) {
  const needsEmail = !user.email
  const needsPassword = Boolean(user.mustChangePassword)
  const required = needsEmail || needsPassword
  const [email, setEmail] = React.useState(user.email ?? "")
  const [currentPassword, setCurrentPassword] = React.useState("")
  const [newPassword, setNewPassword] = React.useState("")
  const [confirmPassword, setConfirmPassword] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)

  React.useEffect(() => setEmail(user.email ?? ""), [user.email])
  if (!required) return null

  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    if (needsEmail && !email.trim()) return setError("Introduce una dirección de correo.")
    if (needsPassword && newPassword.length < 6) return setError("La nueva contraseña debe tener al menos 6 caracteres.")
    if (needsPassword && newPassword !== confirmPassword) return setError("Las contraseñas no coinciden.")
    setSaving(true)
    try {
      if (needsEmail) await api.updateProfileEmail(email)
      if (needsPassword) await api.changePassword(currentPassword, newPassword)
      onComplete()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo actualizar tu cuenta.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      onClose={() => undefined}
      dismissible={false}
      title="Completa tu cuenta"
      description={needsPassword ? "Por seguridad, cambia la contraseña inicial antes de continuar." : "Añade tu correo para terminar de configurar tu cuenta."}
    >
      <form onSubmit={save} className="space-y-4">
        {needsEmail && <div className="space-y-1.5"><label htmlFor="setup-email" className="text-sm font-medium">Correo electrónico</label><Input id="setup-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></div>}
        {needsPassword && <>
          <div className="space-y-1.5"><label htmlFor="setup-current-password" className="text-sm font-medium">Contraseña inicial</label><Input id="setup-current-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></div>
          <div className="space-y-1.5"><label htmlFor="setup-new-password" className="text-sm font-medium">Nueva contraseña</label><Input id="setup-new-password" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></div>
          <div className="space-y-1.5"><label htmlFor="setup-confirm-password" className="text-sm font-medium">Confirmar nueva contraseña</label><Input id="setup-confirm-password" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></div>
        </>}
        {error && <p className="rounded-xl bg-status-failed/10 px-3 py-2 text-sm text-status-failed" role="alert">{error}</p>}
        <Button type="submit" className="w-full" disabled={saving || (needsPassword && !currentPassword)}>{saving && <Spinner className="h-4 w-4" />}Guardar y continuar</Button>
      </form>
    </Modal>
  )
}
