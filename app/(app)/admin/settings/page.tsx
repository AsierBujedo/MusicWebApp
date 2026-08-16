"use client"

import * as React from "react"
import { Save } from "lucide-react"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/providers/toast-provider"

interface Setting {
  key: string
  label: string
  description: string
  type: "toggle" | "number" | "text"
  value: string | number | boolean
}

const DEFAULT_SETTINGS: Setting[] = [
  {
    key: "auto_approve",
    label: "Aprobación automática",
    description: "Descarga peticiones nuevas sin revisión manual de un administrador.",
    type: "toggle",
    value: false,
  },
  {
    key: "allow_requests",
    label: "Permitir peticiones",
    description: "Los usuarios pueden solicitar música que no está en la biblioteca.",
    type: "toggle",
    value: true,
  },
  {
    key: "max_requests",
    label: "Límite de peticiones por usuario",
    description: "Número máximo de peticiones activas simultáneas por usuario.",
    type: "number",
    value: 10,
  },
  {
    key: "quality",
    label: "Calidad de descarga preferida",
    description: "Perfil de calidad usado al buscar en las fuentes.",
    type: "text",
    value: "FLAC / Lossless",
  },
]

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${
        checked ? "bg-primary" : "bg-secondary"
      }`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  )
}

export default function AdminSettingsPage() {
  const { toast } = useToast()
  const [settings, setSettings] = React.useState<Setting[]>(DEFAULT_SETTINGS)
  const [saving, setSaving] = React.useState(false)

  const update = (key: string, value: string | number | boolean) => {
    setSettings((prev) => prev.map((s) => (s.key === key ? { ...s, value } : s)))
  }

  const save = async () => {
    setSaving(true)
    await new Promise((r) => setTimeout(r, 700))
    setSaving(false)
    toast("Ajustes guardados", "success")
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ajustes"
        description="Configura el comportamiento del sistema de peticiones y descargas."
        action={
          <Button onClick={save} disabled={saving}>
            <Save className="h-4 w-4" aria-hidden />
            {saving ? "Guardando..." : "Guardar"}
          </Button>
        }
      />

      <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
        {settings.map((setting) => (
          <div key={setting.key} className="flex items-center gap-4 p-4">
            <div className="min-w-0 flex-1">
              <label htmlFor={setting.key} className="font-medium">
                {setting.label}
              </label>
              <p className="text-sm text-muted-foreground text-pretty">{setting.description}</p>
            </div>
            <div className="shrink-0">
              {setting.type === "toggle" ? (
                <Toggle checked={Boolean(setting.value)} onChange={(v) => update(setting.key, v)} />
              ) : setting.type === "number" ? (
                <Input
                  id={setting.key}
                  type="number"
                  min={1}
                  value={String(setting.value)}
                  onChange={(e) => update(setting.key, Number(e.target.value))}
                  className="w-24 text-center"
                />
              ) : (
                <Input
                  id={setting.key}
                  value={String(setting.value)}
                  onChange={(e) => update(setting.key, e.target.value)}
                  className="w-48"
                />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
