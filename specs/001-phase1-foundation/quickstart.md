# Quickstart: Phase 1 — Foundation

## Prerequisites

- **Docker Desktop** (Windows) with Docker Compose v2
- **Node.js 22+** and **pnpm 9** (`npm i -g pnpm`)
- **Python 3.13** and **uv** (`pip install uv`)
- **Git**

## 1. Clone and Setup Environment

```bash
cd C:\apps\engez

# Copy environment template
cp .env.example .env
# Edit .env with your values (SECRET_KEY, OPENAI_API_KEY, etc.)
```

## 2. Start Backend Services

```bash
# Start PostgreSQL + Redis + API
docker compose up -d

# Verify all services are healthy
docker compose ps
# Expected: postgres (healthy), redis (healthy), api (running)
```

## 3. Run Database Migrations

```bash
# Enter the API container
docker compose exec api bash

# Run Alembic migrations
alembic upgrade head

# Seed initial company and admin
python -m app.services.seed
# Creates: Company "ENGEZ Demo" + Admin user admin@engez.app / <from .env>

exit
```

## 4. Start Frontend Dev Server

```bash
cd frontend
pnpm install
pnpm dev
# Opens at http://localhost:5173
# API requests proxy to http://localhost:8000
```

## 5. Verify Everything Works

1. Open http://localhost:5173 in Chrome
2. Login with seeded admin credentials
3. Verify: Arabic RTL layout, dark mode, IBM Plex Arabic font
4. Open DevTools > Application:
   - Service Worker: registered
   - IndexedDB: EngezDB with expenses, projects, categories, syncQueue tables
   - Manifest: detected with Arabic app name
5. Toggle language to English and back
6. Disconnect network (DevTools > Network > Offline) → app still loads from cache

## Common Issues

**Docker services won't start**: Ensure Docker Desktop is running and ports 5432/6379/8000 are free.

**Alembic migration fails**: Check DATABASE_URL in .env matches the Docker Compose postgres config.

**Fonts not loading**: First load requires internet to fetch from Google Fonts CDN. After caching, they work offline.

**PWA not installing**: Chrome requires HTTPS for PWA install. In dev, use `chrome://flags/#unsafely-treat-insecure-origin-as-secure` and add `http://localhost:5173`.
