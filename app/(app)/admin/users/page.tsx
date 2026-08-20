"use client"

import * as React from "react"
import useSWR, { useSWRConfig } from "swr"
import { UserPlus, MoreHorizontal, Shield, Trash2, Power, BadgeCheck, SlidersHorizontal } from "lucide-react"
import type { Role, User } from "@/types/api"
import { api } from "@/lib/api"
import { useAuth } from "@/components/providers/auth-provider"
import { useToast } from "@/components/providers/toast-provider"
import { PageHeader } from "@/components/page-header"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Modal } from "@/components/ui/modal"
import { Dropdown, DropdownItem } from "@/components/ui/dropdown"
import { formatRelativeDate } from "@/lib/utils"

export default function AdminUsersPage() {
  const { data, isLoading } = useSWR<User[]>("admin:users", () => api.getUsers())
  const { mutate } = useSWRConfig()
  const { toast } = useToast()
  const { user: me } = useAuth()

  const [creating, setCreating] = React.useState(false)
  const [form, setForm] = React.useState({ username: "", displayName: "", email: "", password: "", role: "USER" as Role, autoApproveRequests: false })
  const [saving, setSaving] = React.useState(false)
  const [featureTarget, setFeatureTarget] = React.useState<User | null>(null)
  const [selectedFeatures, setSelectedFeatures] = React.useState<string[]>([])

  const users = data ?? []

  const refresh = () => {
    mutate("admin:users")
    mutate("admin:stats")
  }

  const handleCreate = async () => {
    if (!form.username.trim() || !form.displayName.trim()) return
    setSaving(true)
    try {
      await api.createUser({
        username: form.username.trim(),
        displayName: form.displayName.trim(),
        password: form.password,
        email: form.email.trim() || undefined,
        role: form.role,
        autoApproveRequests: form.role === "USER" && form.autoApproveRequests,
      })
      toast("Usuario creado con su contraseña", "success")
      setCreating(false)
      setForm({ username: "", displayName: "", email: "", password: "", role: "USER", autoApproveRequests: false })
      refresh()
    } catch {
      toast("No se pudo crear el usuario", "error")
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (u: User) => {
    try {
      await api.updateUser(u.id, { active: !u.active })
      toast(u.active ? "Usuario desactivado" : "Usuario activado", "info")
      refresh()
    } catch {
      toast("No se pudo actualizar", "error")
    }
  }

  const toggleRole = async (u: User) => {
    try {
      await api.updateUser(u.id, { role: u.role === "ADMIN" ? "USER" : "ADMIN" })
      toast("Rol actualizado", "info")
      refresh()
    } catch {
      toast("No se pudo actualizar", "error")
    }
  }

  const toggleAutoApproval = async (u: User) => {
    try {
      await api.updateUser(u.id, { autoApproveRequests: !u.autoApproveRequests })
      toast(u.autoApproveRequests ? "Autoaprobación desactivada" : "Solicitudes autoaprobadas", "info")
      refresh()
    } catch {
      toast("No se pudo actualizar", "error")
    }
  }

  const remove = async (u: User) => {
    try {
      await api.deleteUser(u.id)
      toast("Usuario eliminado", "info")
      refresh()
    } catch {
      toast("No se pudo eliminar", "error")
    }
  }
  const openFeatures = (u: User) => { setFeatureTarget(u); setSelectedFeatures(u.featureFlags ?? []) }
  const saveFeatures = async () => {
    if (!featureTarget) return
    try { await api.updateUserFeatureFlags(featureTarget.id, selectedFeatures); toast("Funciones actualizadas", "success"); setFeatureTarget(null); refresh() }
    catch { toast("No se pudieron actualizar las funciones", "error") }
  }
  const toggleFeature = (key: string) => setSelectedFeatures((items) => items.includes(key) ? items.filter((item) => item !== key) : [...items, key])
  const featureOptions = [
    ["admin.users", "Gestionar usuarios", "Crear usuarios normales y activar su autoaprobación."],
    ["admin.requests", "Moderar solicitudes", "Aprobar o rechazar solicitudes de la comunidad."],
    ["admin.library", "Biblioteca completa", "Consultar el catálogo completo de canciones."],
    ["admin.services", "Gestionar servicios", "Ver el estado y ejecutar mantenimiento de servicios."],
    ["admin.demo", "Modo demo", "Entrar temporalmente como una cuenta normal para soporte o pruebas."],
  ] as const

  return (
    <div>
      <PageHeader
        title="Usuarios"
        subtitle="Gestiona quién tiene acceso y con qué permisos."
        action={
          <Button onClick={() => setCreating(true)} className="gap-2">
            <UserPlus className="h-4 w-4" />
            <span className="hidden sm:inline">Añadir</span>
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className="flex items-center gap-3 rounded-2xl border border-border bg-card p-3">
              <Avatar name={u.displayName} src={u.avatar} className="h-11 w-11" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium">{u.displayName}</p>
                  {u.role === "ADMIN" && (
                    <span className="flex items-center gap-1 rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                      <Shield className="h-2.5 w-2.5" />
                      Admin
                    </span>
                  )}
                  {!u.active && (
                    <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground">Inactivo</span>
                  )}
                  {u.role === "USER" && u.autoApproveRequests && (
                    <span className="flex items-center gap-1 rounded-full bg-status-success/15 px-1.5 py-0.5 text-[10px] font-medium text-status-success"><BadgeCheck className="h-2.5 w-2.5" />Autoaprueba</span>
                  )}
                </div>
                <p className="truncate text-xs text-muted-foreground">
                  @{u.username}
                  {u.lastSeen ? ` · visto ${formatRelativeDate(u.lastSeen)}` : ""}
                </p>
              </div>

              {u.id !== me?.id ? (
                <Dropdown
                  trigger={
                    <Button variant="ghost" size="icon-sm" aria-label="Opciones de usuario">
                      <MoreHorizontal className="h-5 w-5" />
                    </Button>
                  }
                >
                  {me?.role === "ADMIN" && <DropdownItem icon={Shield} onClick={() => toggleRole(u)}>
                    {u.role === "ADMIN" ? "Quitar admin" : "Hacer admin"}
                  </DropdownItem>}
                  {me?.role === "ADMIN" && u.role === "USER" && <DropdownItem icon={SlidersHorizontal} onClick={() => openFeatures(u)}>Funciones</DropdownItem>}
                  {me?.role === "ADMIN" && <DropdownItem icon={Power} onClick={() => toggleActive(u)}>
                    {u.active ? "Desactivar" : "Activar"}
                  </DropdownItem>}
                  {u.role === "USER" && <DropdownItem icon={BadgeCheck} onClick={() => toggleAutoApproval(u)}>
                    {u.autoApproveRequests ? "Quitar autoaprobación" : "Autoaprobar solicitudes"}
                  </DropdownItem>}
                  {me?.role === "ADMIN" && <DropdownItem icon={Trash2} destructive onClick={() => remove(u)}>
                    Eliminar
                  </DropdownItem>}
                </Dropdown>
              ) : (
                <span className="px-2 text-xs text-muted-foreground">Tú</span>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Añadir usuario">
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label htmlFor="u-name" className="text-sm font-medium">Nombre</label>
              <Input id="u-name" value={form.displayName} onChange={(e) => setForm((f) => ({ ...f, displayName: e.target.value }))} placeholder="Marta" />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="u-username" className="text-sm font-medium">Usuario</label>
              <Input id="u-username" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} placeholder="marta" />
            </div>
          </div>
          <div className="space-y-1.5">
            <label htmlFor="u-email" className="text-sm font-medium">Email <span className="text-muted-foreground">(opcional)</span></label>
            <Input id="u-email" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} placeholder="marta@home.local" />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="u-password" className="text-sm font-medium">Contraseña</label>
            <Input
              id="u-password"
              type="password"
              minLength={6}
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              placeholder="Mínimo 6 caracteres"
            />
          </div>
          {me?.role === "ADMIN" && <div className="space-y-1.5">
            <span className="text-sm font-medium">Rol</span>
            <div className="flex gap-2">
              {(["USER", "ADMIN"] as Role[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setForm((f) => ({ ...f, role: r }))}
                  className={
                    "flex-1 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors " +
                    (form.role === r ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:text-foreground")
                  }
                >
                  {r === "USER" ? "Usuario" : "Administrador"}
                </button>
              ))}
            </div>
          </div>}
          {form.role === "USER" && (
            <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-3 transition-colors hover:bg-secondary/50">
              <input type="checkbox" checked={form.autoApproveRequests} onChange={(e) => setForm((f) => ({ ...f, autoApproveRequests: e.target.checked }))} className="mt-0.5 h-4 w-4 accent-primary" />
              <span><span className="block text-sm font-medium">Autoaprobar solicitudes</span><span className="mt-0.5 block text-xs text-muted-foreground">Sus solicitudes pasarán directamente a descarga, sin moderación manual.</span></span>
            </label>
          )}
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={() => setCreating(false)}>Cancelar</Button>
            <Button className="flex-1" onClick={handleCreate} disabled={saving || !form.username.trim() || !form.displayName.trim() || form.password.length < 6}>
              {saving ? "Creando…" : "Crear usuario"}
            </Button>
          </div>
        </div>
      </Modal>
      <Modal open={Boolean(featureTarget)} onClose={() => setFeatureTarget(null)} title={`Funciones de ${featureTarget?.displayName ?? ""}`} description="Las funciones de usuario habituales están activas para todos. Estas son funciones delegadas de administración.">
        <div className="space-y-2">
          {featureOptions.map(([key, label, description]) => <label key={key} className="flex cursor-pointer gap-3 rounded-xl border border-border p-3 hover:bg-secondary/50"><input type="checkbox" checked={selectedFeatures.includes(key)} onChange={() => toggleFeature(key)} className="mt-0.5 h-4 w-4 accent-primary" /><span><span className="block text-sm font-medium">{label}</span><span className="block text-xs text-muted-foreground">{description}</span></span></label>)}
          <div className="flex gap-3 pt-2"><Button variant="secondary" className="flex-1" onClick={() => setFeatureTarget(null)}>Cancelar</Button><Button className="flex-1" onClick={() => void saveFeatures()}>Guardar</Button></div>
        </div>
      </Modal>
    </div>
  )
}
