import { cn } from "@/lib/utils"

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
  // The demo artwork route is deterministic: every missing cover gets a
  // distinctive visual identity without flashing to a different image on
  // every render or reload.
  const fallback = `/api/cover?seed=${encodeURIComponent(alt)}`
  return (
    <div className={cn("relative shrink-0 overflow-hidden bg-secondary", rounded, className)}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src || fallback}
        alt={alt}
        loading="lazy"
        className="h-full w-full object-cover"
        onError={(event) => {
          // Covers from external catalogues can disappear or be rate-limited.
          // Replace them once with the local generated artwork.
          if (event.currentTarget.src !== new URL(fallback, window.location.origin).href) event.currentTarget.src = fallback
        }}
      />
    </div>
  )
}
