import { Music } from "lucide-react"
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
  return (
    <div className={cn("relative shrink-0 overflow-hidden bg-secondary", rounded, className)}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src || "/placeholder.svg"} alt={alt} loading="lazy" className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-muted-foreground">
          <Music className="h-1/3 w-1/3" aria-hidden="true" />
        </div>
      )}
    </div>
  )
}
