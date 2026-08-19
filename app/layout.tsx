import type React from "react"
import type { Metadata, Viewport } from "next"
import { Geist, Geist_Mono, Sora } from "next/font/google"
import "./globals.css"
import { Providers } from "@/components/providers"

const geist = Geist({ subsets: ["latin"], variable: "--font-geist" })
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" })
const sora = Sora({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-sora" })

export const metadata: Metadata = {
  title: "Resonar",
  description: "Busca, escucha y solicita música. Una biblioteca privada para toda la familia.",
  manifest: "/manifest.webmanifest",
  applicationName: "Resonar",
  icons: {
    icon: "/icon.png",
    shortcut: "/favicon.ico",
    apple: "/apple-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Resonar",
  },
  formatDetection: { telephone: false },
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#231f2a" },
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" className={`dark ${geist.variable} ${geistMono.variable} ${sora.variable}`} suppressHydrationWarning>
      <body className="bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
