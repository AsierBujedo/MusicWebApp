import type { NextRequest } from "next/server"

// Deterministic, offline album-art generator. Produces a tasteful duotone
// "vinyl" motif from a seed so every track/album has consistent artwork
// without any external image service.

function hash(str: string): number {
  let h = 2166136261
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h)
}

const PALETTES: [string, string, string][] = [
  ["#2a1f3d", "#f2683c", "#f7b267"],
  ["#122a2e", "#3ddc97", "#a8f0d0"],
  ["#2b1a2e", "#e05780", "#ffc2d1"],
  ["#1a2238", "#5c8bff", "#a9c7ff"],
  ["#2e2410", "#f4c04f", "#ffe6a0"],
  ["#241a2e", "#a367ff", "#d7bbff"],
  ["#2e1414", "#ff5c5c", "#ffb4a1"],
  ["#0f2a24", "#28c0a8", "#8ff0dd"],
]

export async function GET(req: NextRequest) {
  const seed = req.nextUrl.searchParams.get("seed") ?? "home-music"
  const h = hash(seed)
  const [bg, accent, light] = PALETTES[h % PALETTES.length]
  const angle = h % 360
  const cx = 30 + (h % 40)
  const cy = 30 + ((h >> 3) % 40)

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <defs>
    <clipPath id="c"><rect width="400" height="400" rx="0"/></clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="400" height="400" fill="${bg}"/>
    <g transform="rotate(${angle} 200 200)">
      <rect x="-120" y="120" width="640" height="70" fill="${accent}" opacity="0.9"/>
      <rect x="-120" y="230" width="640" height="26" fill="${light}" opacity="0.55"/>
    </g>
    <circle cx="${cx * 4}" cy="${cy * 4}" r="150" fill="none" stroke="${light}" stroke-width="2" opacity="0.35"/>
    <circle cx="${cx * 4}" cy="${cy * 4}" r="110" fill="none" stroke="${light}" stroke-width="2" opacity="0.3"/>
    <circle cx="${cx * 4}" cy="${cy * 4}" r="70" fill="${accent}" opacity="0.9"/>
    <circle cx="${cx * 4}" cy="${cy * 4}" r="16" fill="${bg}"/>
  </g>
</svg>`

  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  })
}
