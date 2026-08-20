"use client"

import { useRouter } from "next/navigation"
import * as React from "react"
import type { User } from "@/types/api"
import { Modal } from "@/components/ui/modal"
import { Button } from "@/components/ui/button"

export function AccountSetupModal({ user }: { user: User }) {
  const router = useRouter()
  const [dismissed, setDismissed] = React.useState(false)
  const needsEmail = !user.email
  // Administrators may be bootstrap/maintenance accounts. Their password
  // lifecycle is managed separately, so never show the initial-password
  // reminder to them.  They can still receive the independent email prompt.
  const needsPassword = user.role !== "ADMIN" && Boolean(user.mustChangePassword)
  if ((!needsEmail && !needsPassword) || dismissed) return null

  const description = needsEmail && needsPassword
    ? "Añade tu correo y cambia la contraseña inicial desde tu perfil. Te lo recordaremos al volver a iniciar sesión hasta que lo completes."
    : needsPassword
      ? "Te recomendamos cambiar la contraseña inicial desde tu perfil. Te lo recordaremos al volver a iniciar sesión hasta que la cambies."
      : "Añade una dirección de correo desde tu perfil. Te lo recordaremos al volver a iniciar sesión hasta que lo hagas."

  return (
    <Modal open onClose={() => setDismissed(true)} title="Completa tu cuenta" description={description}>
      <Button className="w-full" onClick={() => { setDismissed(true); router.push("/profile") }}>Ir a mi perfil</Button>
    </Modal>
  )
}
