"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

const FALLBACK_COVERS = [
  "/fallback-covers/abstract-01.webp",
  "/fallback-covers/abstract-02.webp",
  "/fallback-covers/abstract-03.webp",
  "/fallback-covers/abstract-04.webp",
  "/fallback-covers/abstract-05.webp",
  "/fallback-covers/abstract-06.webp",
  "/fallback-covers/abstract-07.webp",
  "/fallback-covers/abstract-08.webp",
  "/fallback-covers/abstract-09.webp",
  "/fallback-covers/abstract-10.webp",
]

function fallbackFor(seed: string) {
  let value = 0
  for (let index = 0; index < seed.length; index += 1) value = (value * 31 + seed.charCodeAt(index)) >>> 0
  return FALLBACK_COVERS[value % FALLBACK_COVERS.length]
}

export function CoverImage({
  src,
  alt,
  className,
  rounded = "rounded-lg",
}: {
  src?: string
  alt: string
  className?: string
  rounded?: string
}) {
  // The generated cover is always rendered first. It gives every item a stable
  // identity while an upstream image is still loading (or has disappeared).
  const fallback = fallbackFor(alt)
  const [loaded, setLoaded] = React.useState(!src)

  React.useEffect(() => setLoaded(!src), [src])

  return (
    <div className={cn("relative shrink-0 overflow-hidden bg-secondary", rounded, className)}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={fallback} alt={src ? "" : alt} aria-hidden={src ? true : undefined} className="h-full w-full object-cover" />
      {src && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className={cn("absolute inset-0 h-full w-full object-cover transition-opacity duration-300", loaded ? "opacity-100" : "opacity-0")}
          onLoad={() => setLoaded(true)}
          onError={() => setLoaded(false)}
        />
      )}
    </div>
  )
}
