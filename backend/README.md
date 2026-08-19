# Home Music Assistant — Backend

A production-ready **FastAPI** backend for the Home Music Assistant web app. It
implements the exact `/api/*` contract the Next.js frontend expects
(`types/api.ts` + `lib/real-api.ts`), including cookie-based auth, a music
request lifecycle with a background worker, and a Server-Sent Events (SSE)
realtime stream.

## Features

- **Cookie session auth** with Argon2 password hashing (`/api/auth/*`).
- **Role-based access control** (`ADMIN` / `USER`) with an always-present admin.
- **Library + search** aggregated across three pluggable providers
  (Navidrome, DroppedNeedle, slskd) behind a clean adapter interface.
- **Music request lifecycle** — `PENDING → APPROVED → SEARCHING → DOWNLOADING → AVAILABLE`
  (or `FAILED` / `REJECTED`), driven by a background worker.
- **Realtime updates** over SSE (`/api/events`) with `request.updated` and
  `track.updated` frames matching the frontend's `RealtimeEvent` shape.
- **Favorites, play history, and playlists** (with track ordering).
- **Admin** endpoints: dashboard stats, service health, request moderation, and
  full user management.
- **Audio streaming** with HTTP Range support (`/api/stream/{trackId}`).
- **Mockable integrations** — runs fully offline with realistic seed data via
  `MOCK_EXTERNAL_SERVICES=true`, so it drops straight into the existing frontend
  mock catalog.

## Tech stack

| Concern        | Choice                                   |
| -------------- | ---------------------------------------- |
| Framework      | FastAPI + Uvicorn                        |
| Data           | SQLAlchemy 2.0 ORM + Alembic migrations  |
| Database       | SQLite (dev) / PostgreSQL (prod)         |
| Auth           | Signed session cookies + Argon2 hashing  |
| Realtime       | Server-Sent Events (`sse`)               |
| Tests          | pytest + FastAPI TestClient              |

## Project layout

```
backend/
├── app/
│   ├── main.py            # App factory, middleware, lifespan, worker startup
│   ├── config.py          # Pydantic settings (env-driven)
│   ├── database.py        # Engine, SessionLocal, Base, get_db
│   ├── bootstrap.py       # Seeds the initial admin user
│   ├── dependencies.py    # Auth/session FastAPI dependencies
│   ├── core/              # security, cookies, permissions, SSE event manager
│   ├── models/            # SQLAlchemy models (+ to_public serializers)
│   ├── schemas/           # Pydantic request/response schemas (camelCase)
│   ├── routers/           # One module per API area
│   └── services/          # Business logic + integration adapters
│       └── integrations/  # Navidrome / DroppedNeedle / slskd + mocks
├── alembic/               # Migration environment + versions
├── tests/                 # pytest suite (auth, library, requests, admin)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml     # API + Postgres
└── .env.example
```

## Quick start (local, SQLite + mocks)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # defaults work out of the box
uvicorn app.main:app --reload --port 8000
```

The service boots with mock providers, seeds an `admin` / `admin` account, and
serves interactive docs at `http://localhost:8000/docs`.

## Connecting the frontend

The Next.js app switches from its built-in mock to this backend via two env vars
(set them in the frontend project, not here):

```bash
NEXT_PUBLIC_MOCK_API=false
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Because auth uses cookies with `credentials: "include"`, set `FRONTEND_ORIGIN`
on the backend to your frontend's exact origin (e.g. `http://localhost:3000`).
This enables `CORS` with credentials and, for cross-site setups, switches the
session cookie to `SameSite=None; Secure`.

## Environment variables

See `.env.example` for the full list. Highlights:

| Variable                  | Default        | Purpose                                            |
| ------------------------- | -------------- | -------------------------------------------------- |
| `DATABASE_URL`            | SQLite file    | SQLAlchemy connection string                       |
| `SECRET_KEY`              | —              | Signs session cookies (**required in prod**)       |
| `SESSION_COOKIE_NAME`     | `hma_session`  | Session cookie name                                |
| `FRONTEND_ORIGIN`         | —              | Allowed CORS origin(s), comma-separated            |
| `MOCK_EXTERNAL_SERVICES`  | `true`         | Use in-memory mock providers instead of real ones  |
| `DROPPEDNEEDLE_URL` / credentials | — | DroppedNeedle API v1 endpoint plus its service username/password |
| `NAVIDROME_URL` / creds   | —              | Navidrome (Subsonic API) library provider          |
| `DROPPEDNEEDLE_URL` / key | —              | DroppedNeedle requestable-catalog provider         |
| `SLSKD_URL` / key         | —              | slskd (Soulseek) download provider                 |
| `BOOTSTRAP_ADMIN_*`       | `admin`/`admin`| Initial admin credentials (seeded once)            |

## API surface

All routes are under `/api`. Auth is via the session cookie set on login.

- `POST /api/auth/login` · `POST /api/auth/logout` · `GET /api/auth/me` · `POST /api/auth/password`
- `GET /api/search?q=` · `GET /api/tracks/{id}` · `GET /api/stream/{id}` (Range)
- `GET/POST /api/requests` · `POST /api/requests/{id}/retry`
- `GET/POST/DELETE /api/favorites`
- `GET /api/history` · `POST /api/history`
- `GET/POST /api/playlists` · `GET/PATCH/DELETE /api/playlists/{id}` · item add/remove/reorder
- `GET /api/events` (SSE realtime stream)
- `GET /api/admin/stats` · `GET /api/admin/services` · request moderation · user CRUD
- `GET /api/health`

## Realtime events (SSE)

`GET /api/events` streams JSON frames matching the frontend `RealtimeEvent` union:

```
data: {"type":"request.updated","requestId":"...","status":"DOWNLOADING","progress":50}
data: {"type":"track.updated","trackId":"...","status":"AVAILABLE"}
```

Regular members receive events for their own requests; admins receive all.

## Migrations (Alembic)

```bash
alembic upgrade head                          # apply migrations
alembic revision --autogenerate -m "message"  # create a new migration
```

On SQLite/dev the app also calls `create_all` at startup, so migrations are
optional locally but recommended for Postgres/production.

## Tests

```bash
pytest
```

The suite exercises auth + RBAC, library/search/favorites/history/playlists, the
full request lifecycle to `AVAILABLE`, range streaming, admin stats/services, and
the "cannot remove the last admin" guard.

## Docker

```bash
# API (SQLite persisted in ./data)
docker compose up --build

# API only (SQLite), mocks on
docker build -t hma-backend .
docker run -p 8000:8000 -e SECRET_KEY=change-me hma-backend
```

## Going live with real providers

Set `MOCK_EXTERNAL_SERVICES=false` and provide the relevant `*_URL` and
credential variables. DroppedNeedle uses `DROPPEDNEEDLE_USERNAME` and
`DROPPEDNEEDLE_PASSWORD`; its server-side bearer token is never exposed to the
browser. Each provider is isolated in
`app/services/integrations/`; the aggregation, request lifecycle, and API
contract are unchanged whether providers are mocked or real.
