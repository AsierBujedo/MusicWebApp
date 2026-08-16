# Resonar — Home Music

Aplicación web (PWA) para buscar, escuchar y solicitar música desde una
biblioteca privada. Frontend en **Next.js 16 (App Router) + React + TypeScript
+ Tailwind CSS v4**.

Incluye reproductor persistente con controles en la pantalla de bloqueo
(reproducción en segundo plano), zona de usuario (inicio, búsqueda,
solicitudes, favoritos, listas, historial, perfil) y panel de administración
(estadísticas, usuarios, moderación de solicitudes, estado de servicios y
ajustes).

---

## Requisitos

- **Node.js 18.18+** (recomendado 20 o superior)
- **npm** (o pnpm/yarn/bun; los ejemplos usan npm)

## Puesta en marcha (desarrollo)

```bash
# 1. Instalar dependencias
npm install

# 2. Arrancar el servidor de desarrollo
npm run dev
```

Abre **http://localhost:3000**.

Por defecto la app arranca en **modo demo (mock)**: no necesita backend y trae
datos de ejemplo. Puedes entrar con:

- Usuario administrador: `admin`
- Usuario normal: `demo`
- Contraseña: cualquiera

## Scripts

| Script          | Descripción                                    |
| --------------- | ---------------------------------------------- |
| `npm run dev`   | Servidor de desarrollo con recarga en caliente |
| `npm run build` | Compilación de producción                      |
| `npm run start` | Sirve la build de producción                   |
| `npm run lint`  | Linter                                         |

## Producción

```bash
npm run build
npm run start   # sirve en http://localhost:3000
```

---

## Modo demo vs. backend real

La app habla con una interfaz `MusicApi` que tiene dos implementaciones
(`lib/mock/mock-api.ts` y `lib/real-api.ts`). Se elige con una variable de
entorno:

| Variable                | Valor          | Efecto                                      |
| ----------------------- | -------------- | ------------------------------------------- |
| `NEXT_PUBLIC_MOCK_API`  | `true` (o sin definir) | Modo demo con datos simulados       |
| `NEXT_PUBLIC_MOCK_API`  | `false`        | Usa el backend real vía HTTP                |
| `NEXT_PUBLIC_API_URL`   | p. ej. `https://api.midominio.com` | Base del backend. Vacío = mismo origen (`/api/*`) |

Crea un archivo `.env.local` para configurarlo:

```bash
# .env.local — conectar al backend real
NEXT_PUBLIC_MOCK_API=false
NEXT_PUBLIC_API_URL=            # vacío si el backend se sirve en el mismo origen
```

El cliente real espera endpoints bajo `/api/*` (login, búsqueda, streaming en
`/api/stream/:id`, solicitudes, favoritos, listas, historial, eventos en tiempo
real por SSE en `/api/events`, y rutas de administración). La sesión se maneja
con una cookie **HttpOnly** puesta por el backend.

### Variables del backend

Estas variables las consume el **backend** (no el frontend Next.js) y ya están
provisionadas en el entorno del proyecto:

`DATABASE_URL`, `NAVIDROME_URL`, `SLSKD_URL`, `DROPPEDNEEDLE_URL`,
`FRONTEND_ORIGIN`, `SECRET_KEY`, `SESSION_COOKIE_NAME`.

---

## PWA e instalación

La app es instalable como PWA (manifest en `app/manifest.ts`, con nombre, icono
y colores de tema).

- **iPhone / iPad (Safari):** Compartir → «Añadir a pantalla de inicio».
- **Android (Chrome):** menú ⋮ → «Instalar aplicación».
- **Escritorio (Chrome/Edge):** icono de instalar en la barra de direcciones.

### Reproducción en segundo plano

El reproductor usa la **MediaSession API**, así que:

- La música **sigue sonando** aunque cambies de app, bloquees el móvil o se
  apague la pantalla.
- Aparecen **controles en la pantalla de bloqueo / Dynamic Island / centro de
  control** (play, pausa, anterior, siguiente y barra de progreso) con la
  carátula y los datos de la canción.

> Nota: el sonido real en segundo plano requiere el **backend real**
> (`NEXT_PUBLIC_MOCK_API=false`), que sirve el audio. En modo demo se muestran
> los metadatos y controles, pero no hay archivos de audio reales.

### Notch / Dynamic Island

La interfaz respeta las *safe areas* del dispositivo (`viewport-fit=cover` +
`env(safe-area-inset-*)`), de modo que la barra superior y el reproductor no
quedan tapados por el Dynamic Island ni por la barra de estado al usarse como
PWA a pantalla completa.

---

## Estructura del proyecto

```
app/
  (app)/            Rutas autenticadas (inicio, búsqueda, admin, perfil…)
  api/cover/        Generación de carátulas SVG deterministas
  layout.tsx        Metadatos, fuentes, viewport (safe areas) y providers
  manifest.ts       Manifiesto PWA
components/
  layout/           Shell: sidebar, top bar, nav móvil, reproductor
  providers/        Auth, player (MediaSession), realtime, tema, toasts, biblioteca
  ui/               Primitivas de interfaz
lib/
  api.ts            Selector mock/real
  api-types.ts      Interfaz MusicApi
  mock/             Implementación demo
  real-api.ts       Cliente HTTP del backend
types/              Tipos de dominio
```
