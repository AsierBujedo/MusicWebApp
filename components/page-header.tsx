import { cn } from "@/lib/utils"

export function PageHeader({
  title,
  subtitle,
  description,
  action,
  className,
}: {
  title: string
  subtitle?: string
  description?: string
  action?: React.ReactNode
  className?: string
}) {
  const sub = subtitle ?? description
  return (
    <div className={cn("mb-6 flex items-end justify-between gap-4", className)}>
      <div className="min-w-0">
        <h1 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl text-balance">{title}</h1>
        {sub && <p className="mt-1 text-sm text-muted-foreground text-pretty">{sub}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
