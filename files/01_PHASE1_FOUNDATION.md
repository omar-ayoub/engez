# Phase 1: Foundation — Weeks 1–3

## Spec-Kit Commands for Phase 1

Run these in Claude Code before writing any code:

```bash
/speckit.specify
# Paste the following specification prompt:
```

> **Specification Prompt for Phase 1:**
>
> Build the foundation layer of a field expense capture Progressive Web App targeting Egyptian enterprises in construction, event management, and freight logistics.
>
> The app serves two primary user roles: field workers who capture expenses rapidly in remote locations with poor connectivity, and accountants who review and approve those expenses from an office.
>
> Phase 1 delivers: a complete Arabic-first RTL design system, project scaffolding with offline-first architecture, JWT-based multi-tenant authentication with three roles (field_worker, accountant, admin), and a PostgreSQL database schema supporting expenses, projects, users, companies, and AI correction feedback.
>
> The field worker experience must feel as fast as sending a WhatsApp message — under 15 seconds from app open to expense submitted. Arabic (Egyptian dialect) is the default language. English is a toggle. Dark mode is the default theme.
>
> Multi-tenancy is mandatory: every record is scoped to a company_id. Data isolation between tenants is enforced at the database query level.

```bash
/speckit.clarify
/speckit.plan
# Paste the following plan prompt:
```

> **Plan Prompt for Phase 1:**
>
> Use React 19.2 with TypeScript 6.0 and Vite 8 (Rolldown). Use vite-plugin-pwa with Workbox 7 for PWA capabilities. Use Dexie.js 4.4 for IndexedDB offline storage. Use shadcn/ui with RTL mode enabled and Tailwind CSS 4. Use IBM Plex Arabic as primary font. Backend uses FastAPI 0.136 on Python 3.13 with SQLAlchemy 2.0 async, Alembic migrations, and PostgreSQL 16. JWT auth with python-jose using RS256. Docker Compose for local development on Windows. pnpm as package manager.

```bash
/speckit.tasks
/speckit.analyze
/speckit.implement
```

---

## Task 1.1: Project Scaffold (Days 1–2)

### Frontend Scaffold

```bash
# Create Vite React TypeScript project
pnpm create vite frontend --template react-ts

cd frontend

# Install core dependencies (exact versions for reproducibility)
pnpm add react@^19.2.0 react-dom@^19.2.0
pnpm add react-router@^7.0.0
pnpm add dexie@^4.4.0 dexie-react-hooks@^1.1.0
pnpm add zustand@^5.0.0
pnpm add react-i18next@^15.0.0 i18next@^24.0.0 i18next-browser-languagedetector@^8.0.0
pnpm add react-hook-form@^7.54.0
pnpm add @tanstack/react-query@^5.0.0

# Install dev dependencies
pnpm add -D vite-plugin-pwa@^0.21.0 workbox-window@^7.3.0
pnpm add -D @types/react@^19.0.0 @types/react-dom@^19.0.0
pnpm add -D tailwindcss@^4.0.0 @tailwindcss/vite@^4.0.0
pnpm add -D typescript@^6.0.0
pnpm add -D vitest@^3.0.0 @testing-library/react@^16.0.0
pnpm add -D @vitejs/plugin-react@^6.0.0

# Initialize shadcn/ui with RTL support
pnpm dlx shadcn@latest init --rtl
# When prompted:
#   Style: New York
#   Base color: Neutral
#   RTL: Yes
#   Primitive library: Radix UI
```

### Vite Configuration

Create `frontend/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico", "apple-touch-icon.png", "mask-icon.svg"],
      manifest: {
        name: "مصروف — Masrouf Field Expense",
        short_name: "مصروف",
        description: "Field expense capture for Egyptian enterprises",
        theme_color: "#0D9488",
        background_color: "#0A0A0A",
        display: "standalone",
        orientation: "portrait",
        dir: "rtl",
        lang: "ar",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\..*/i,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: { maxEntries: 200, maxAgeSeconds: 86400 },
              cacheableResponse: { statuses: [0, 200] },
              networkTimeoutSeconds: 5,
            },
          },
          {
            urlPattern: /\.(?:woff2?|ttf|otf)$/i,
            handler: "CacheFirst",
            options: {
              cacheName: "font-cache",
              expiration: { maxEntries: 10, maxAgeSeconds: 31536000 },
            },
          },
        ],
        // Background sync for offline expense submissions
        // This is critical — expenses queued offline replay on reconnect
      },
      devOptions: {
        enabled: true, // Enable PWA in development for testing
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

### TypeScript Configuration

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "forceConsistentCasingInFileNames": true,
    "allowImportingTsExtensions": true,
    "moduleDetection": "force",
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src", "vite-env.d.ts"]
}
```

### Backend Scaffold

```bash
mkdir -p backend/app/{api/v1,core,models,schemas,services}
mkdir -p backend/alembic backend/tests

cd backend

# Create pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "masrouf-api"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]==0.136.1",
    "uvicorn[standard]==0.34.0",
    "sqlalchemy[asyncio]==2.0.38",
    "asyncpg==0.30.0",
    "alembic==1.14.1",
    "pydantic==2.13.3",
    "pydantic-settings==2.8.0",
    "python-jose[cryptography]==3.4.0",
    "passlib[bcrypt]==1.7.4",
    "python-multipart==0.0.20",
    "pillow==11.1.0",
    "pyzbar==0.1.9",
    "openai==1.82.0",
    "httpx==0.28.1",
    "pywebpush==2.0.1",
    "py-vapid==1.9.2",
    "boto3==1.38.0",
    "redis==5.2.0",
    "orjson==3.11.8",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.4",
    "pytest-asyncio==0.25.0",
    "httpx==0.28.1",
    "ruff==0.15.8",
]
EOF

# Install with uv
uv sync
```

### Docker Compose (Local Development)

Create `docker-compose.yml` in project root:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: masrouf
      POSTGRES_USER: masrouf
      POSTGRES_PASSWORD: dev_password_change_in_prod
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U masrouf"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://masrouf:dev_password_change_in_prod@postgres:5432/masrouf
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: dev-secret-key-change-in-prod
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      R2_ACCOUNT_ID: ${R2_ACCOUNT_ID}
      R2_ACCESS_KEY: ${R2_ACCESS_KEY}
      R2_SECRET_KEY: ${R2_SECRET_KEY}
      R2_BUCKET: masrouf-receipts
      ENVIRONMENT: development
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: fastapi dev app/main.py --host 0.0.0.0 --port 8000

volumes:
  pgdata:
  redisdata:
```

### Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.13-slim

# Install system dependencies for pyzbar (QR decoding)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzbar0 \
    libzbar-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy application code
COPY . .

# Default command (overridden in docker-compose for dev)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Task 1.2: Design System (Days 3–5)

### Install shadcn/ui Components

```bash
cd frontend

# Core components needed for expense app
pnpm dlx shadcn@latest add button input card badge toast \
  dialog sheet tabs avatar separator label textarea \
  select dropdown-menu popover command scroll-area \
  skeleton alert switch tooltip direction
```

### shadcn/ui RTL Configuration

Ensure `frontend/components.json` has RTL enabled:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/index.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "rtl": true
}
```

### Global CSS with Arabic Typography

Create `frontend/src/index.css`:

```css
@import "tailwindcss";

/* IBM Plex Arabic — loaded from Google Fonts CDN */
@font-face {
  font-family: "IBM Plex Arabic";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("https://fonts.gstatic.com/s/ibmplexsansarabic/v12/Qw3CZRtWPQCuHme67tEYUIx3Kh0PHR9N6bs61A.woff2")
    format("woff2");
}

@font-face {
  font-family: "IBM Plex Arabic";
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url("https://fonts.gstatic.com/s/ibmplexsansarabic/v12/Qw3NZRtWPQCuHme67tEYUIx3Kh0PHR9N6YPy_eCRXMR.woff2")
    format("woff2");
}

@font-face {
  font-family: "IBM Plex Arabic";
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url("https://fonts.gstatic.com/s/ibmplexsansarabic/v12/Qw3NZRtWPQCuHme67tEYUIx3Kh0PHR9N6YOW_OCRXMRj.woff2")
    format("woff2");
}

@theme {
  --font-sans: "IBM Plex Arabic", "IBM Plex Sans", system-ui, sans-serif;
  --font-mono: "IBM Plex Mono", monospace;

  /* Brand colors */
  --color-brand: #0D9488;
  --color-brand-light: #14B8A6;
  --color-accent: #F59E0B;
  --color-success: #10B981;
  --color-danger: #F43F5E;
}

/* Ensure RTL direction on html */
:root {
  direction: rtl;
}

/* Amount display — always LTR for numbers */
.amount-display {
  direction: ltr;
  unicode-bidi: embed;
  font-variant-numeric: tabular-nums;
  font-family: "IBM Plex Mono", monospace;
}

/* Touch target minimum for field workers */
.touch-target {
  min-height: 44px;
  min-width: 44px;
}
```

### Run Impeccable Document Command

After creating the design system, run in Claude Code:

```bash
/impeccable document
# This scans codebase and writes DESIGN.md in Google Stitch format
```

Then run the initial audit:

```bash
/impeccable audit
# Catches AI slop patterns, ensures no purple gradients, Inter font, etc.
```

---

## Task 1.3: Authentication System (Days 6–8)

### Backend: JWT Auth with Multi-Tenancy

Create `backend/app/core/security.py`:

```python
"""JWT authentication with RS256 and multi-tenant isolation."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenPayload(BaseModel):
    sub: str          # user_id
    company_id: str   # tenant isolation
    role: str         # field_worker | accountant | admin
    exp: datetime

def create_access_token(
    user_id: str,
    company_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return TokenPayload(**payload)
    except JWTError:
        raise ValueError("Invalid token")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

Create `backend/app/core/config.py`:

```python
"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Masrouf API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours for field workers

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET: str = "masrouf-receipts"
    R2_PUBLIC_URL: str = ""

    # VAPID for Web Push
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_CLAIMS_EMAIL: str = ""

    model_config = {"env_file": ".env", "case_sensitive": True}

settings = Settings()
```

### Frontend: Auth Context and Route Guards

Create `frontend/src/lib/auth.ts`:

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  name: string;
  email: string;
  role: "field_worker" | "accountant" | "admin";
  companyId: string;
  companyName: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token, user) =>
        set({ token, user, isAuthenticated: true }),
      logout: () =>
        set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: "masrouf-auth",
      // Persists to localStorage so field workers stay logged in
    }
  )
);
```

---

## Task 1.4: Database Schema (Days 9–11)

### SQLAlchemy Models

Create `backend/app/models/base.py`:

```python
"""Base model with common fields and multi-tenant mixin."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

class TenantMixin:
    """Every tenant-scoped model must include company_id."""
    company_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
```

Create `backend/app/models/expense.py`:

```python
"""Expense model — the core entity."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Numeric,
    String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_registration: Mapped[Optional[str]] = mapped_column(String(50))
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)


class User(Base, TimestampMixin, TenantMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="field_worker"
    )  # field_worker | accountant | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    push_subscription: Mapped[Optional[dict]] = mapped_column(JSONB)


class Project(Base, TimestampMixin, TenantMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Expense(Base, TimestampMixin, TenantMixin):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_company_status", "company_id", "status"),
        Index("ix_expenses_company_project", "company_id", "project_id"),
        Index("ix_expenses_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id")
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), default="EGP", nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(String(255))
    vendor_tax_reg: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500))
    receipt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    voice_transcript: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending | approved | rejected
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)
    eta_uuid: Mapped[Optional[str]] = mapped_column(String(64))
    eta_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_extraction: Mapped[Optional[dict]] = mapped_column(JSONB)
    ai_confidence: Mapped[Optional[dict]] = mapped_column(JSONB)
    anomaly_flags: Mapped[Optional[dict]] = mapped_column(JSONB)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    offline_id: Mapped[Optional[str]] = mapped_column(String(36))


class CorrectionFeedback(Base, TimestampMixin, TenantMixin):
    """Stores accountant corrections to AI extractions.
    Used as few-shot examples in future extraction prompts.
    THIS IS THE COMPOUNDING MOAT."""
    __tablename__ = "correction_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    expense_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("expenses.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_value: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )


class VendorCache(Base, TimestampMixin, TenantMixin):
    """Caches vendor names by tax registration number.
    Accelerates future submissions after first encounter."""
    __tablename__ = "vendor_cache"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    tax_registration: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(255))
    category_hint: Mapped[Optional[str]] = mapped_column(String(100))
```

### Dexie.js Offline Schema (Mirrors Server)

Create `frontend/src/lib/db.ts`:

```typescript
import Dexie, { type EntityTable } from "dexie";

// Mirror backend schema for offline-first storage

export interface OfflineExpense {
  id: string;            // UUID generated client-side
  userId: string;
  projectId?: string;
  amount: number;
  currency: string;
  category: string;
  vendor?: string;
  vendorTaxReg?: string;
  notes?: string;
  receiptBlob?: Blob;    // Stored locally until synced
  receiptUrl?: string;   // Set after upload
  voiceBlob?: Blob;      // Voice recording blob
  voiceTranscript?: string;
  status: "draft" | "pending" | "synced" | "approved" | "rejected";
  etaUuid?: string;
  etaVerified: boolean;
  aiExtraction?: Record<string, unknown>;
  aiConfidence?: Record<string, number>;
  createdAt: Date;
  syncedAt?: Date;
  syncError?: string;
}

export interface OfflineProject {
  id: string;
  companyId: string;
  name: string;
  nameAr: string;
  code: string;
  budget?: number;
  isActive: boolean;
}

export interface SyncQueueItem {
  id: string;
  type: "expense" | "expense_update";
  payload: string;       // JSON stringified
  retryCount: number;
  createdAt: Date;
  lastAttempt?: Date;
}

const db = new Dexie("MasroufDB") as Dexie & {
  expenses: EntityTable<OfflineExpense, "id">;
  projects: EntityTable<OfflineProject, "id">;
  syncQueue: EntityTable<SyncQueueItem, "id">;
};

db.version(1).stores({
  expenses: "id, userId, projectId, status, createdAt, syncedAt",
  projects: "id, companyId, code, isActive",
  syncQueue: "id, type, createdAt, retryCount",
});

export { db };
```

### Run Alembic Migration

```bash
cd backend

# Initialize Alembic
alembic init alembic

# Edit alembic/env.py to use async engine and import models
# Then generate initial migration
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

---

## Task 1.5: i18n Setup (Day 12)

### Arabic-First Internationalization

Create `frontend/public/locales/ar/common.json`:

```json
{
  "app": {
    "name": "مصروف",
    "tagline": "إدارة مصروفات الميدان"
  },
  "nav": {
    "home": "الرئيسية",
    "expenses": "المصروفات",
    "projects": "المشاريع",
    "settings": "الإعدادات"
  },
  "expense": {
    "new": "مصروف جديد",
    "amount": "المبلغ",
    "category": "الفئة",
    "vendor": "المورد",
    "project": "المشروع",
    "notes": "ملاحظات",
    "submit": "إرسال",
    "pending": "في الانتظار",
    "approved": "تم الموافقة",
    "rejected": "مرفوض",
    "voice": "تسجيل صوتي",
    "camera": "صورة الإيصال",
    "savedLocally": "محفوظ محلياً — سيتم المزامنة عند الاتصال",
    "synced": "تمت المزامنة",
    "etaVerified": "تم التحقق من الفاتورة الإلكترونية"
  },
  "auth": {
    "login": "تسجيل الدخول",
    "email": "البريد الإلكتروني",
    "password": "كلمة المرور",
    "logout": "تسجيل الخروج"
  },
  "status": {
    "online": "متصل",
    "offline": "غير متصل",
    "syncing": "جاري المزامنة..."
  }
}
```

Create `frontend/public/locales/en/common.json` (mirror structure in English).

Create `frontend/src/lib/i18n.ts`:

```typescript
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "ar",
    defaultNS: "common",
    ns: ["common"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
    },
    resources: {
      // Loaded inline for offline-first — no network fetch needed
      ar: { common: require("../../public/locales/ar/common.json") },
      en: { common: require("../../public/locales/en/common.json") },
    },
  });

export default i18n;
```

---

## Phase 1 Completion Checklist

Run `/impeccable audit` after completing Phase 1 to verify:

- [ ] Frontend builds with `pnpm build` — zero errors
- [ ] Backend starts with `docker compose up` — all services healthy
- [ ] shadcn/ui components render correctly in RTL mode
- [ ] Arabic text displays with IBM Plex Arabic font
- [ ] Dark mode is active by default
- [ ] PWA manifest is detected by browser (check DevTools > Application)
- [ ] Service worker registers in development mode
- [ ] Dexie.js IndexedDB initializes with correct schema
- [ ] JWT login flow works (API returns token, frontend stores it)
- [ ] Route guards redirect unauthenticated users to login
- [ ] Alembic migrations run cleanly against PostgreSQL
- [ ] Docker Compose brings up all 3 services (postgres, redis, api)
- [ ] No Impeccable anti-pattern violations

**Proceed to `02_PHASE2_CORE_CAPTURE.md` →**
