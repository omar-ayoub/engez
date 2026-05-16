# Quickstart: Core Expense Capture

**Phase**: 1 — Design & Contracts | **Date**: 2026-05-15

## New Backend Dependencies

Add to `backend/pyproject.toml` dependencies:

```toml
"openai>=1.40,<2",         # gpt-4o-mini-transcribe + gpt-4o vision
"pyzbar==0.23.0",          # ETA QR code decoding from receipt images
"Pillow>=11.0,<12",        # Image preprocessing (contrast enhancement for thermal receipts)
"boto3>=1.35,<2",          # Cloudflare R2 (S3-compatible) blob storage
```

Install: `cd backend && uv sync`

## New Frontend Dependencies

Add to `frontend/package.json`:

```bash
cd frontend && pnpm add dexie-react-hooks@^1.1
```

`dexie-react-hooks` provides the `useLiveQuery` hook for reactive Dexie queries (live pending counts, draft counts, vendor search results).

## Environment Variables

Add to `.env` (and `.env.example`):

```bash
# OpenAI (required for voice + receipt AI processing)
OPENAI_API_KEY=sk-...

# Cloudflare R2 (required for blob storage)
R2_ACCOUNT_ID=...
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=engez-receipts
R2_PUBLIC_URL=https://r2.engez.app

# Rate limiting (optional, defaults shown)
AI_RATE_LIMIT_VOICE=100      # per company per hour
AI_RATE_LIMIT_RECEIPT=100    # per company per hour
```

**Notes**:
- `OPENAI_API_KEY`, `R2_*` are already defined in `backend/app/core/config.py` from Phase 1 (with empty defaults). They now become required for Phase 2 functionality.
- Rate limit settings are new and should be added to `config.py`.

## Vite Config Change

The service worker strategy changes from `generateSW` (auto) to `injectManifest` (custom). This requires:

1. Creating `frontend/src/sw/service-worker.ts` (the custom service worker)
2. Updating the VitePWA config in `frontend/vite.config.ts`:

```typescript
VitePWA({
  strategies: "injectManifest",
  srcDir: "src/sw",
  filename: "service-worker.ts",
  registerType: "autoUpdate",
  injectManifest: {
    globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
  },
  // manifest stays the same
  manifest: { /* ... existing manifest ... */ },
  devOptions: { enabled: true, type: "module" },
})
```

The existing `workbox.runtimeCaching` config is removed (moved into the custom service worker code).

## Dexie Schema Migration

`frontend/src/lib/db.ts` must be updated to version 2:
- Add `captureMode` index to expenses
- Add `vendorCache` table
- Add upgrade function for existing data

See [data-model.md](data-model.md) for the full schema definition.

## i18n Namespace

Add a new `capture` namespace for capture-specific UI strings:

- `frontend/public/locales/ar/capture.json`
- `frontend/public/locales/en/capture.json`

Load the namespace in the capture feature pages via `useTranslation('capture')`.

## Docker Compose

No changes required. The backend container already has Python 3.13 which supports all new dependencies. pyzbar requires `libzbar0` which must be added to the backend Dockerfile:

```dockerfile
# Add before pip install
RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*
```

## Testing Setup

### Backend
- Mock OpenAI calls with `httpx` response fixtures (don't call real API in tests)
- Use fixture receipt images with known ETA QR codes for QR decode tests
- Redis mock via `fakeredis` for rate limiter tests

### Frontend
- Vitest + Testing Library React for component tests
- Mock `navigator.mediaDevices.getUserMedia` for voice capture tests
- Mock Dexie with `fake-indexeddb` for offline storage tests
