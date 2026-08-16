"use client"

import Link from "next/link"
import { Play } from "lucide-react"
import { CoverImage } from "@/components/cover-image"
import { cn } from "@/lib/utils"

export function MediaCard({
  title,
  subtitle,
  cover,
  href,
  rounded,
  onPlay,
}: {
  title: string
  subtitle?: string
  cover?: string
  href?: string
  rounded?: boolean
  onPlay?: () => void
}) {
  const inner = (
    <div className="group relative">
      <div className="relative">
        <CoverImage
          src={cover}
          alt={title}
          className={cn("aspect-square w-full", rounded ? "rounded-full" : "rounded-2xl")}
        />
        {onPlay && (
          <button
            onClick={(e) => {
              e.preventDefault()
              onPlay()
            }}
            aria-label={`Reproducir ${title}`}
            className="absolute bottom-2 right-2 flex h-11 w-11 translate-y-2 items-center justify-center rounded-full bg-primary text-primary-foreground opacity-0 shadow-lg transition-all group-hover:translate-y-0 group-hover:opacity-100"
          >
            <Play className="h-5 w-5 translate-x-0.5 fill-current" />
          </button>
        )}
      </div>
      <div className={cn("mt-2", rounded && "text-center")}>
        <p className="truncate text-sm font-medium">{title}</p>
        {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
      </div>
    </div>
  )

  if (href) {
    return (
      <Link href={href} className="block">
        {inner}
      </Link>
    )
  }
  return inner
}

export function MediaCardSkeleton({ rounded }: { rounded?: boolean }) {
  return (
    <div>
      <div className={cn("skeleton aspect-square w-full", rounded ? "rounded-full" : "rounded-2xl")} />
      <div className="mt-2 space-y-1.5">
        <div className="skeleton h-3.5 w-3/4 rounded" />
        <div className="skeleton h-3 w-1/2 rounded" />
      </div>
    </div>
  )
}
