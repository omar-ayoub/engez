# Known Conflicts & Pre-Resolved Issues

## Purpose

This document catalogs dependency conflicts, compatibility issues, and common pitfalls identified during research — resolved before a single line of code is written.

---

## 1. Vite 8 + vite-plugin-pwa Compatibility

**Issue:** Vite 8 switched from Rollup to Rolldown internally. The `vite-plugin-pwa` package (last published Nov 2025) was built against Vite 5/6 APIs. Breaking changes in `build.rollupOptions` → `build.rolldownOptions`.

**Resolution:**
- Pin `vite-plugin-pwa@0.21.x` which has Vite 7 compatibility
- If Vite 8 breaks the plugin, downgrade to `vite@^7.0.0` (still fully supported, Node 20.19+)
- Monitor the [vite-pwa GitHub](https://github.com/vite-pwa/vite-plugin-pwa) for a Vite 8 compatible release
- **Fallback stack:** Vite 7 + vite-plugin-pwa 0.21.x is a stable combination

```bash
# If Vite 8 causes issues:
pnpm add vite@^7.0.0 @vitejs/plugin-react@^5.0.0
```

---

## 2. React 19 + TypeScript 6.0 Type Changes

**Issue:** React 19 introduced breaking TypeScript type changes:
- `JSX` is no longer in the global namespace → use `React.JSX`
- `useRef()` without arguments is now an error → use `useRef(undefined)`
- `RefObject<T>` from `useRef(null)` is now `RefObject<T | null>`

**Resolution:**
- Ensure `@types/react@^19.0.0` and `@types/react-dom@^19.0.0` are installed
- Run the codemod if migrating from React 18: `npx types-react-codemod@latest preset-19 ./src`
- Since this is a greenfield project, use React 19 patterns from the start

```typescript
// CORRECT in React 19
const ref = useRef<HTMLInputElement>(null); // Returns RefObject<HTMLInputElement | null>

// ref.current is HTMLInputElement | null — check before use
if (ref.current) {
  ref.current.focus();
}
```

---

## 3. Tailwind CSS 4 + shadcn/ui Configuration

**Issue:** Tailwind CSS 4 changed its configuration approach. The `tailwind.config.ts` file is replaced by CSS-based configuration using `@theme` directives. The `@tailwindcss/vite` plugin is the recommended integration.

**Resolution:**
- Use `@tailwindcss/vite` plugin (not PostCSS)
- Configure themes in `src/index.css` using `@theme` blocks
- shadcn/ui's `init --rtl` handles the Tailwind 4 configuration automatically
- Do NOT create a `tailwind.config.ts` — Tailwind 4 uses CSS-first config

```css
/* src/index.css — Tailwind 4 configuration */
@import "tailwindcss";

@theme {
  --font-sans: "IBM Plex Arabic", "IBM Plex Sans", system-ui, sans-serif;
  --color-primary: #0D9488;
  /* ... other theme tokens */
}
```

---

## 4. Dexie.js 4 + Service Worker Context

**Issue:** Dexie.js uses IndexedDB which is available in both the main thread and service workers, but `dexie-react-hooks` (useLiveQuery) only works in React components. The service worker needs direct Dexie access for sync operations.

**Resolution:**
- Import `dexie` (not `dexie-react-hooks`) in the service worker
- Create a shared schema file that both main thread and service worker can import
- Use `dexie-react-hooks` only in React components
- In the service worker, use raw Dexie queries for sync queue processing

```typescript
// src/lib/db-schema.ts — shared between main thread and SW
export const DB_NAME = "MasroufDB";
export const DB_VERSION = 1;
export const STORES = {
  expenses: "id, userId, projectId, status, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  syncQueue: "id, type, createdAt, retryCount",
};
```

---

## 5. pyzbar on Docker (Alpine Linux)

**Issue:** `pyzbar` requires `libzbar` system library. On Alpine-based Docker images, the package name is different and may not include shared libraries.

**Resolution:**
- Use `python:3.13-slim` (Debian-based) instead of `python:3.13-alpine`
- Install `libzbar0` and `libzbar-dev` via `apt-get`
- This adds ~15MB to the image but avoids compilation issues

```dockerfile
# Debian-based — pyzbar works out of the box
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 libzbar-dev \
    && rm -rf /var/lib/apt/lists/*
```

---

## 6. OpenAI API Rate Limits

**Issue:** With multiple field workers submitting simultaneously, OpenAI API rate limits may be hit for both Whisper transcription and GPT-4o vision.

**Resolution:**
- Implement request queuing with Redis-backed rate limiting
- Use `gpt-4o-mini` (not `gpt-4o`) for text extraction from voice — cheaper and faster
- Use `gpt-4o` only for receipt image OCR where vision quality matters
- Add retry with exponential backoff for 429 responses
- Consider caching: same vendor + similar amount = skip AI for repeat expenses

```python
# backend/app/services/rate_limiter.py
import asyncio
from redis.asyncio import Redis

async def rate_limited_openai_call(redis: Redis, func, *args, **kwargs):
    """Rate limit OpenAI calls to stay within tier limits."""
    key = "openai:rate_limit"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)  # Reset every minute

    if current > 50:  # 50 requests per minute limit
        wait = await redis.ttl(key)
        await asyncio.sleep(wait)

    return await func(*args, **kwargs)
```

---

## 7. Background Sync API Browser Support

**Issue:** The Background Sync API is not supported in all browsers. Safari/iOS has limited support. Firefox has partial support.

**Resolution:**
- Background Sync is the primary path (Chrome/Edge on Android — main target audience)
- Implement a fallback: when Background Sync is unavailable, use a polling mechanism that checks `navigator.onLine` and retries from the Dexie sync queue
- The app should work on iOS Safari via the polling fallback — just without automatic background sync

```typescript
// Registration with fallback
async function registerSync() {
  const registration = await navigator.serviceWorker.ready;

  if ("sync" in registration) {
    // Background Sync API available
    await registration.sync.register("expense-sync");
  } else {
    // Fallback: manual sync on visibility change
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && navigator.onLine) {
        manualSyncFromQueue();
      }
    });
  }
}
```

---

## 8. Arabic Font Loading and FOUT

**Issue:** IBM Plex Arabic is loaded from Google Fonts CDN. On slow Egyptian mobile networks, there can be a Flash of Unstyled Text (FOUT) where system Arabic fonts appear briefly.

**Resolution:**
- Use `font-display: swap` in @font-face declarations (already configured)
- Include fonts in the PWA precache via Workbox glob patterns (`*.woff2`)
- Self-host the font files in `frontend/public/fonts/` for offline-first reliability
- After initial load, fonts are cached by the service worker and load instantly

```bash
# Download and self-host instead of CDN
mkdir -p frontend/public/fonts
# Download woff2 files from Google Fonts and place them here
```

---

## 9. CORS Configuration for R2 Image URLs

**Issue:** Receipt images stored in Cloudflare R2 need CORS headers to be displayed in the PWA. Without proper CORS, `<img>` tags may load but Canvas-based operations (zoom, rotate) will fail.

**Resolution:**
- Configure R2 bucket CORS rules to allow your domain
- Use signed URLs with short expiry for security
- Alternatively, proxy receipt images through your API if R2 CORS is problematic

```json
// R2 CORS configuration
[
  {
    "AllowedOrigins": ["https://your-domain.com"],
    "AllowedMethods": ["GET"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 86400
  }
]
```

---

## 10. Multi-Tenant Data Isolation

**Issue:** Every database query must be scoped to `company_id`. A single missed filter leaks data between tenants — this is a critical security concern for enterprise clients like Orascom and Hassan Allam.

**Resolution:**
- Use a FastAPI dependency that injects `company_id` from the JWT token
- Create a base query function that automatically adds the tenant filter
- Add database-level Row-Level Security (RLS) as a defense-in-depth measure
- Write automated tests that verify cross-tenant queries return empty results

```python
# backend/app/api/deps.py — always inject tenant scope
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_tenant_scope(
    current_user = Depends(get_current_user),
):
    """Every query MUST use this to filter by company_id."""
    return current_user.company_id
```

---

## 11. Windows Docker Volume Performance

**Issue:** Docker Desktop on Windows uses WSL2 for Linux containers. File system access from Windows host to Docker containers is slow due to cross-filesystem translation (Windows NTFS ↔ Linux ext4).

**Resolution:**
- Store project files inside WSL2 filesystem (e.g., `\\wsl$\Ubuntu\home\user\projects\`)
- Access from VSCode using the "Remote - WSL" extension
- This gives native Linux filesystem speed for Docker volume mounts
- Alternatively, use Docker volume mounts only for database data (pgdata, redisdata) and rebuild containers for code changes

```powershell
# Option A: Work from WSL2 filesystem
wsl
cd ~/projects/field-expense-pwa
code .  # Opens VSCode with WSL remote

# Option B: If working from Windows filesystem, minimize bind mounts
# Use Docker Compose with only data volumes, not code bind mounts
# Rebuild container on code changes: docker compose build api
```

---

## 12. Spec-Kit + Claude Code Integration

**Issue:** Spec-Kit requires specific integration setup for Claude Code. The `--integration claude-code` flag creates `.claude/skills/` files. If Impeccable is also installed, skill conflicts may arise.

**Resolution:**
- Initialize Spec-Kit first, then install Impeccable
- Spec-Kit skills go in `.claude/commands/` (slash commands)
- Impeccable skills go in `.claude/skills/` (design skills)
- They operate in different namespaces and do not conflict
- If issues arise, check that `.claude/` directory structure matches expected layout

```bash
# Correct order:
speckit init field-expense-pwa --integration claude-code
# Creates .claude/commands/ with /speckit.* commands

npx impeccable skills add pbakaus/impeccable
# Installs to .claude/skills/ with /impeccable.* commands
```

---

## Version Lock Summary

Pin these exact versions in your package.json / pyproject.toml to avoid surprises:

### Frontend (package.json)

```json
{
  "react": "^19.2.0",
  "react-dom": "^19.2.0",
  "typescript": "^6.0.0",
  "vite": "^8.0.0",
  "vite-plugin-pwa": "^0.21.0",
  "dexie": "^4.4.0",
  "zustand": "^5.0.0",
  "react-router": "^7.0.0",
  "react-i18next": "^15.0.0",
  "react-hook-form": "^7.54.0",
  "recharts": "^2.15.0",
  "@tailwindcss/vite": "^4.0.0",
  "tailwindcss": "^4.0.0"
}
```

### Backend (pyproject.toml)

```toml
[project]
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]==0.136.1",
    "sqlalchemy[asyncio]==2.0.38",
    "pydantic==2.13.3",
    "pydantic-settings==2.8.0",
    "asyncpg==0.30.0",
    "alembic==1.14.1",
    "python-jose[cryptography]==3.4.0",
    "passlib[bcrypt]==1.7.4",
    "pillow==11.1.0",
    "pyzbar==0.1.9",
    "openai==1.82.0",
    "httpx==0.28.1",
    "pywebpush==2.0.1",
    "redis==5.2.0",
    "boto3==1.38.0",
    "orjson==3.11.8",
]
```

### Infrastructure

```
Docker Engine: 27.x
Docker Compose: 2.x
PostgreSQL: 16-alpine
Redis: 7-alpine
Nginx: 1.27-alpine
Python: 3.13-slim
Node.js: 22.x LTS
pnpm: 9.x
Ubuntu: 24.04 LTS (VPS)
```
