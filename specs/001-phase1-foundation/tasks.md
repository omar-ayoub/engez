# Tasks: Phase 1 — Foundation

**Input**: Design documents from `specs/001-phase1-foundation/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/auth.md, contracts/admin.md, quickstart.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/app/` for Python backend, `frontend/src/` for React frontend

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding, Docker environment, and base configuration files.

- [x] T001 Create frontend project with Vite React TypeScript template — run `pnpm create vite frontend --template react-ts` from project root, then `cd frontend && pnpm install`. This creates `frontend/package.json`, `frontend/src/`, and `frontend/index.html`. After creation, remove the default Vite boilerplate files (`frontend/src/App.css`, `frontend/src/assets/react.svg`, `frontend/public/vite.svg`) that will be replaced by custom files in later tasks.

- [x] T002 Create backend directory structure — create all directories: `backend/app/core/`, `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/api/v1/`, `backend/alembic/`, `backend/tests/`. Create empty `__init__.py` files in each Python package directory: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`, `backend/app/services/__init__.py`, `backend/app/api/__init__.py`, `backend/app/api/v1/__init__.py`.

- [x] T003 [P] Create `backend/pyproject.toml` — define project name "engez-api" version "0.1.0", requires-python ">=3.13". Dependencies: fastapi[standard]==0.136.1, uvicorn[standard]==0.34.0, sqlalchemy[asyncio]==2.0.38, asyncpg==0.30.0, alembic==1.14.1, pydantic==2.13.3, pydantic-settings==2.8.0, python-jose[cryptography]==3.4.0, passlib[bcrypt]==1.7.4, python-multipart==0.0.20, httpx==0.28.1, redis==5.2.0, orjson==3.11.8. Dev dependencies: pytest==8.3.4, pytest-asyncio==0.25.0, httpx==0.28.1, ruff==0.15.8. Then run `cd backend && uv sync` to install.

- [x] T004 [P] Create `docker-compose.yml` at project root — three services: (1) `postgres`: image postgres:16-alpine, env POSTGRES_DB=engez POSTGRES_USER=engez POSTGRES_PASSWORD=dev_password_change_in_prod, port 5432:5432, named volume pgdata, healthcheck `pg_isready -U engez` every 5s. (2) `redis`: image redis:7-alpine, port 6379:6379, named volume redisdata, healthcheck `redis-cli ping` every 5s. (3) `api`: build from ./backend/Dockerfile, port 8000:8000, env DATABASE_URL=postgresql+asyncpg://engez:dev_password_change_in_prod@postgres:5432/engez REDIS_URL=redis://redis:6379/0 SECRET_KEY=dev-secret-key-change-in-prod, plus ${OPENAI_API_KEY} ${R2_ACCOUNT_ID} ${R2_ACCESS_KEY} ${R2_SECRET_KEY} R2_BUCKET=engez-receipts ENVIRONMENT=development, volume ./backend:/app, depends_on postgres and redis (condition: service_healthy), command `fastapi dev app/main.py --host 0.0.0.0 --port 8000`. Declare volumes pgdata and redisdata.

- [x] T005 [P] Create `backend/Dockerfile` — FROM python:3.13-slim. Install system deps for pyzbar: `apt-get update && apt-get install -y --no-install-recommends libzbar0 libzbar-dev && rm -rf /var/lib/apt/lists/*`. WORKDIR /app. Copy uv from ghcr.io/astral-sh/uv:latest to /usr/local/bin/uv. COPY pyproject.toml, run `uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev`. COPY all. CMD `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`. Do NOT run as root in production — add `RUN adduser --disabled-password --no-create-home appuser` and `USER appuser` before CMD (constitution Principle VI: Docker non-root).

- [x] T006 [P] Create `.env.example` at project root — template file documenting every required environment variable with placeholder values and comments: `DATABASE_URL=postgresql+asyncpg://engez:dev_password_change_in_prod@localhost:5432/engez`, `REDIS_URL=redis://localhost:6379/0`, `SECRET_KEY=change-this-to-a-random-64-char-string`, `OPENAI_API_KEY=sk-...`, `R2_ACCOUNT_ID=`, `R2_ACCESS_KEY=`, `R2_SECRET_KEY=`, `R2_BUCKET=engez-receipts`, `R2_PUBLIC_URL=`, `VAPID_PRIVATE_KEY=`, `VAPID_PUBLIC_KEY=`, `VAPID_CLAIMS_EMAIL=`, `SEED_ADMIN_EMAIL=admin@engez.app`, `SEED_ADMIN_PASSWORD=change-this-password`, `ENVIRONMENT=development`.

- [x] T007 [P] Create `.gitignore` — comprehensive ignore rules for: `node_modules/`, `.env`, `*.env.local`, `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `.vite/`, `coverage/`, `.pytest_cache/`, `.DS_Store`, `*.log`, `backend/.venv/`, `frontend/node_modules/`, `alembic/versions/__pycache__/`, `.ruff_cache/`, `*.sqlite3`.

- [x] T008 Configure `frontend/vite.config.ts` — import react from @vitejs/plugin-react, VitePWA from vite-plugin-pwa, tailwindcss from @tailwindcss/vite, path. Plugins: react(), tailwindcss(), VitePWA (registerType autoUpdate, includeAssets favicon/apple-touch-icon/mask-icon, manifest with name "إنجز — ENGEZ Field Expense" short_name "إنجز" description "تطبيق إدارة مصروفات الميدان" theme_color "#0D9488" background_color "#0A0A0A" display standalone orientation portrait dir rtl lang ar start_url "/" scope "/" icons 192+512+maskable, workbox with globPatterns `**/*.{js,css,html,ico,png,svg,woff2}` and runtimeCaching for API NetworkFirst 5s timeout and fonts CacheFirst 1yr, devOptions enabled true). Resolve alias @ → ./src. Server proxy /api → http://localhost:8000 with changeOrigin.

- [x] T009 [P] Configure `frontend/tsconfig.json` — target ES2022, lib ES2022/DOM/DOM.Iterable, module ESNext, moduleResolution bundler, jsx react-jsx, strict true, noEmit true, isolatedModules true, skipLibCheck true, esModuleInterop true, resolveJsonModule true, forceConsistentCasingInFileNames true, allowImportingTsExtensions true, moduleDetection force, noUnusedLocals true, noUnusedParameters true, noFallthroughCasesInSwitch true, baseUrl ".", paths `@/*` → `./src/*`. Include src and vite-env.d.ts.

- [x] T010 [P] Install frontend dependencies — run in `frontend/`: `pnpm add react@^19.2.0 react-dom@^19.2.0 react-router@^7.0.0 dexie@^4.4.0 dexie-react-hooks@^1.1.0 zustand@^5.0.0 react-i18next@^15.0.0 i18next@^24.0.0 i18next-browser-languagedetector@^8.0.0 react-hook-form@^7.54.0` and `pnpm add -D vite-plugin-pwa@^0.21.0 workbox-window@^7.3.0 @types/react@^19.0.0 @types/react-dom@^19.0.0 tailwindcss@^4.0.0 @tailwindcss/vite@^4.0.0 typescript@^6.0.0 vitest@^3.0.0 @testing-library/react@^16.0.0 @vitejs/plugin-react@^6.0.0`.

- [x] T011 Initialize shadcn/ui with RTL support — run `pnpm dlx shadcn@latest init` in `frontend/` with settings: style New York, baseColor neutral, RTL yes, rsc false. Then install core components: `pnpm dlx shadcn@latest add button input card badge toast dialog sheet label select skeleton alert switch separator`. Verify `frontend/components.json` has `"rtl": true`. Verify components are created in `frontend/src/components/ui/`.

- [x] T012 Create `frontend/src/index.css` — Start with `@import "tailwindcss";`. Add three @font-face rules for IBM Plex Arabic (weights 400, 600, 700) with font-display swap and woff2 sources from Google Fonts CDN. Add @theme block defining: `--font-sans: "IBM Plex Arabic", "IBM Plex Sans", system-ui, sans-serif`, `--font-mono: "IBM Plex Mono", monospace`, brand colors `--color-brand: #0D9488`, `--color-brand-light: #14B8A6`, `--color-accent: #F59E0B`, `--color-success: #10B981`, `--color-danger: #F43F5E`. Add `:root { direction: rtl; }`. Add `.amount-display` class (direction ltr, unicode-bidi embed, font-variant-numeric tabular-nums, font-family IBM Plex Mono). Add `.touch-target` class (min-height 44px, min-width 44px). Include shadcn/ui CSS variables for dark mode as default theme (dark background neutral-950, foreground neutral-50).

**Checkpoint**: Project scaffolding complete. All config files in place. Docker Compose can start. Frontend builds with zero errors (may have empty app).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend infrastructure that MUST be complete before ANY user story can be implemented.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T013 Create `backend/app/core/config.py` — Pydantic BaseSettings class named Settings with fields: APP_NAME (str, default "ENGEZ API"), ENVIRONMENT (str, default "development"), DEBUG (bool, default False), DATABASE_URL (str, required), REDIS_URL (str, default "redis://localhost:6379/0"), SECRET_KEY (str, required), ACCESS_TOKEN_EXPIRE_MINUTES (int, default 30 — per research R1), REFRESH_TOKEN_EXPIRE_DAYS (int, default 7 — per research R1), OPENAI_API_KEY (str, default ""), R2_ACCOUNT_ID (str, default ""), R2_ACCESS_KEY (str, default ""), R2_SECRET_KEY (str, default ""), R2_BUCKET (str, default "engez-receipts"), R2_PUBLIC_URL (str, default ""), VAPID_PRIVATE_KEY (str, default ""), VAPID_PUBLIC_KEY (str, default ""), VAPID_CLAIMS_EMAIL (str, default ""), SEED_ADMIN_EMAIL (str, default "admin@engez.app"), SEED_ADMIN_PASSWORD (str, default "changeme123"). Model config: env_file=".env", case_sensitive=True. Export singleton `settings = Settings()`.

- [x] T014 Create `backend/app/core/database.py` — Import create_async_engine and async_sessionmaker from SQLAlchemy. Create async engine from settings.DATABASE_URL with echo=False (True if DEBUG), pool_size=20, max_overflow=10. Create async_session_factory using async_sessionmaker(engine, expire_on_commit=False). Define async generator `get_db()` that yields a session and commits on success / rollbacks on exception. This is the FastAPI dependency for database access.

- [x] T015 Create `backend/app/models/base.py` — Import DeclarativeBase, Mapped, mapped_column from SQLAlchemy ORM. Define `class Base(DeclarativeBase): pass`. Define `class TimestampMixin` with created_at (DateTime timezone=True, default now UTC, server_default text("now()")) and updated_at (same + onupdate now UTC). Define `class TenantMixin` with company_id (String(36), index=True, nullable=False) — per constitution Principle III, every tenant-scoped record MUST have company_id.

- [x] T016 [P] Create `backend/app/models/company.py` — Company model extending Base and TimestampMixin (NOT TenantMixin — Company IS the tenant). Fields per data-model.md: id String(36) PK default uuid4, name String(255) NOT NULL, name_ar String(255) NOT NULL, tax_registration String(50) nullable, is_active Boolean default True, settings JSONB default dict. Table name "companies".

- [x] T017 Create `backend/app/models/user.py` — User model extending Base, TimestampMixin, TenantMixin. Fields per data-model.md: id String(36) PK default uuid4, email String(255) UNIQUE NOT NULL, name String(255) NOT NULL, name_ar String(255) NOT NULL, hashed_password String(255) NOT NULL, role String(20) NOT NULL default "field_worker", is_active Boolean default True, failed_login_attempts Integer default 0, locked_until DateTime(timezone=True) nullable, push_subscription JSONB nullable, webauthn_credential_id String(255) nullable, webauthn_public_key Text nullable. Table name "users". Note: company_id comes from TenantMixin.

- [x] T018 Create `backend/app/core/security.py` — (1) JWT functions: `create_access_token(user_id, company_id, role)` → encodes JWT with sub=user_id, company_id, role, exp=now+ACCESS_TOKEN_EXPIRE_MINUTES using HS256 and settings.SECRET_KEY. `create_refresh_token(user_id)` → encodes JWT with sub=user_id, type="refresh", exp=now+REFRESH_TOKEN_EXPIRE_DAYS*1440 min. `verify_access_token(token)` → decodes and returns TokenPayload(sub, company_id, role, exp) or raises ValueError. `verify_refresh_token(token)` → decodes and returns RefreshPayload(sub, exp) or raises ValueError. (2) Password functions: `hash_password(plain)` → bcrypt hash via passlib CryptContext. `verify_password(plain, hashed)` → bcrypt verify. (3) Pydantic models: TokenPayload, RefreshPayload.

- [x] T019 Create `backend/app/core/deps.py` — FastAPI dependency functions: (1) `get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db))` — extract Bearer token from Authorization header using OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login"), call verify_access_token, query User by id, raise 401 HTTPException if not found. (2) `get_current_active_user(user=Depends(get_current_user))` — check user.is_active and user.company.is_active (join load), raise 403 if inactive. (3) `require_admin(user=Depends(get_current_active_user))` — check user.role == "admin", raise 403 if not. (4) `get_tenant_scope(user=Depends(get_current_active_user))` — returns user.company_id for use in tenant-filtered queries. All HTTP exceptions return bilingual detail (Arabic + detail_en).

- [x] T020 Create `backend/app/main.py` — Create FastAPI app with title="ENGEZ API", version="0.1.0". Add CORSMiddleware allowing origins ["http://localhost:5173", "http://localhost:3000"] with credentials=True (needed for httpOnly cookies), allow methods=["*"], allow headers=["*"]. Import and include the v1 router (from app.api.v1). Add GET /health endpoint returning `{"status": "ok", "environment": settings.ENVIRONMENT}`. Add lifespan context manager that logs startup/shutdown.

- [x] T021 Initialize Alembic — run `cd backend && alembic init alembic` inside the API container (or locally). Edit `backend/alembic/env.py`: set `target_metadata = Base.metadata`, import Base from app.models.base, import all models (Company, User) so they register with Base. Configure async engine: replace `run_migrations_online()` with async version using `create_async_engine` and `run_sync`. Edit `backend/alembic.ini`: set `sqlalchemy.url` to empty string (will be overridden by env.py using settings.DATABASE_URL). Verify alembic can connect by running `alembic current` (should show no revision).

- [ ] T022 Start Docker Compose and verify — run `docker compose up -d`. Check `docker compose ps` shows all three services healthy (postgres, redis, api). Check `docker compose logs api` shows FastAPI startup. Test health endpoint: `curl http://localhost:8000/health` returns `{"status": "ok"}`. If any service fails, debug and fix before proceeding.

**Checkpoint**: Foundation ready — database engine connects, Alembic initialized, FastAPI serves requests, auth dependencies defined. User story implementation can now begin.

---

## Phase 3: User Story 1 — Field Worker Logs In and Sees Home Screen (Priority: P1)

**Goal**: A field worker opens the app, logs in with email/password, and sees a home screen in Arabic RTL dark mode. Returning users bypass login. Locked accounts show calm error.

**Independent Test**: Log in with seeded credentials → home screen renders in Arabic RTL with dark mode, shows user name and company. Reopen app → still logged in. Enter wrong password 5 times → account locks with Arabic message.

### Implementation for User Story 1

- [x] T023 [US1] Create `backend/app/schemas/auth.py` — Pydantic models: `LoginRequest(email: str, password: str)`, `UserInfo(id: str, email: str, name: str, name_ar: str, role: str, company_id: str, company_name: str, company_name_ar: str)`, `LoginResponse(access_token: str, token_type: str = "bearer", user: UserInfo)`, `TokenRefreshResponse(access_token: str, token_type: str = "bearer")`. All models use Pydantic v2 `model_config = ConfigDict(from_attributes=True)`.

- [x] T024 [US1] Create `backend/app/services/auth_service.py` — AuthService class with async methods: (1) `authenticate_user(db, email, password)` → query User by email (join Company for company_name), check if locked (locked_until > now → raise HTTPException 423 with Arabic message and locked_until), verify password (if fail → increment failed_login_attempts, if reaches 5 → set locked_until=now+15min, commit, raise 401), on success → reset failed_login_attempts to 0, commit, return user. (2) `create_tokens(user)` → call create_access_token and create_refresh_token from security module, return both. (3) `refresh_access_token(db, refresh_token_str)` → verify_refresh_token, query user by sub, check is_active, create new access token only, return it. Check that company.is_active too — if not, raise 403 "الحساب غير نشط".

- [x] T025 [US1] Create `backend/app/api/v1/auth.py` — APIRouter with prefix="/auth", tags=["auth"]. Endpoints: (1) `POST /login` — accept LoginRequest body, call auth_service.authenticate_user, call create_tokens, set refresh_token as httpOnly secure sameSite=strict cookie (max_age=7*24*3600, path="/api/v1/auth"), return LoginResponse with access_token and UserInfo. (2) `POST /refresh` — read refresh_token from request.cookies, call auth_service.refresh_access_token, return TokenRefreshResponse. (3) `POST /logout` — delete refresh_token cookie by setting max_age=0, return {"logged_out": true}. (4) `POST /webauthn/register` — accept credential_id + public_key + attestation, store on current user (requires get_current_active_user), return {"registered": true}. (5) `POST /webauthn/authenticate` — accept WebAuthn assertion, verify signature against stored public_key, if valid → create_tokens and return LoginResponse, if invalid → 401 "فشل التحقق البيومتري". All error responses include both Arabic detail and detail_en fields.

- [x] T026 [US1] Create `backend/app/api/v1/__init__.py` — Create `v1_router = APIRouter(prefix="/api/v1")`. Include auth_router from auth.py. (Other routers will be added in US2 tasks.) Export v1_router.

- [x] T027 [US1] Generate Alembic migration for Company and User tables — run `alembic revision --autogenerate -m "add companies and users tables"` inside the API container. Verify the generated migration creates: `companies` table with all fields from data-model.md, `users` table with all fields including failed_login_attempts/locked_until/webauthn fields, foreign key users.company_id → companies.id, unique constraint on users.email, index on users.company_id. Run `alembic upgrade head`. Verify tables exist with `\dt` in psql.

- [x] T028 [US1] Create `frontend/src/lib/api.ts` — Export an `api` object with methods `get(url)`, `post(url, body)`, `patch(url, body)`, `delete(url)`. Each method: reads accessToken from auth store, sets Authorization Bearer header if present, sets Content-Type application/json, calls fetch with credentials "include" (for httpOnly cookies). On 401 response: attempt silent refresh by calling POST /api/v1/auth/refresh (credentials include), if refresh succeeds → update accessToken in auth store → retry original request once, if refresh fails → call auth store logout() and redirect to /login. Parse response as JSON. On error responses: extract `detail` (Arabic) and `detail_en` fields, throw structured error. Base URL defaults to "" (same origin, Vite proxy handles in dev).

- [x] T029 [US1] Create `frontend/src/lib/auth.ts` — Zustand store using `create<AuthState>()(persist(...))`. State: `user: UserInfo | null`, `accessToken: string | null`, `isAuthenticated: boolean`. Actions: `login(accessToken, user)` sets all three, `logout()` clears all three, `setAccessToken(token)` updates token only (for silent refresh). Persist config: name "engez-auth", partialize to persist only `user` and `isAuthenticated` (NOT accessToken — it lives in memory only, refreshed via cookie on reload). On app load, if isAuthenticated is true but accessToken is null → trigger a /refresh call to get a new access token from the cookie.

- [x] T030 [US1] Create `frontend/src/hooks/useOnlineStatus.ts` — Custom React hook: initialize state from `navigator.onLine`. Add event listeners for `window 'online'` and `window 'offline'` events, update state accordingly. Clean up listeners on unmount. Return `{ isOnline: boolean }`.

- [x] T031 [US1] Create `frontend/src/pages/Login.tsx` — Full login page component using React Hook Form and shadcn/ui components. Layout: dark background (bg-neutral-950), centered card (max-w-sm), "إنجز" app name in IBM Plex Arabic 700 weight at top with brand teal color, subtitle text. Form fields: (1) email Input with type="email", label from t('auth.email'), placeholder, RTL text alignment, 44px min-height touch target. (2) password Input with type="password", label from t('auth.password'), 44px min-height. (3) Submit Button with text t('auth.login'), full width, brand teal background (#0D9488), hover brand-light (#14B8A6), 44px min-height, loading state with spinner during API call. Error handling: on 401 show calm toast with t('auth.invalidCredentials'), on 423 show toast with t('auth.accountLocked') and remaining lockout time, on network error show t('status.offline') message. On success: call auth.login(), navigate to "/". All text uses t() for i18n. CSS uses logical properties (ms-*, me-*, ps-*, pe-*) for RTL.

- [x] T032 [US1] Create `frontend/src/pages/Home.tsx` — Home screen component. Top section: welcome message with user.name_ar from auth store, company badge showing user.company_name_ar, role badge (field_worker → "عامل ميدان", accountant → "محاسب", admin → "مدير") using shadcn Badge. Middle section: placeholder card for "مصروف جديد" (new expense) primary action — large touch target button with + icon, brand teal, 44px+ height, positioned for thumb reach. Bottom section: sync status bar showing online/offline indicator from useOnlineStatus hook with icon and Arabic label. Dark theme throughout (bg-neutral-950, text-neutral-50). All spacing uses Tailwind logical properties. All strings via t().

- [x] T033 [US1] Create `frontend/src/App.tsx` — Root component wrapping: (1) BrowserRouter from react-router, (2) Route definitions: "/" → Home (protected), "/login" → Login (public). (3) Auth guard: if not authenticated → redirect to /login, if authenticated and on /login → redirect to /. (4) On mount: if auth store has isAuthenticated=true but no accessToken → call POST /api/v1/auth/refresh to restore session from httpOnly cookie. (5) Import and execute i18n setup (side-effect import). (6) Wrap children with direction provider that sets document.dir based on current i18n language.

- [x] T034 [US1] Create `frontend/src/main.tsx` — Import React and ReactDOM, import `./lib/i18n` (side-effect to initialize i18next before render), import `./index.css` (Tailwind + fonts + theme), import App component. Call `ReactDOM.createRoot(document.getElementById('root')!)` and render `<App />`. Set `document.documentElement.dir = 'rtl'` and `document.documentElement.lang = 'ar'` as initial defaults before React hydrates.

**Checkpoint**: At this point, the login → home screen flow should work end-to-end. Field worker can log in, see Arabic RTL dark mode home screen, and the session persists across app reloads. Account lockout works after 5 failed attempts.

---

## Phase 4: User Story 2 — Admin Creates a Company and Users (Priority: P2)

**Goal**: Admin users can manage their company details, create/update users with roles, manage projects and categories — all via REST API with full tenant isolation.

**Independent Test**: Seed admin logs in → creates a second user (field_worker role) → lists users (sees only their company's users) → creates a project with code and budget → creates expense categories. A second company's admin sees zero data from the first company.

### Implementation for User Story 2

- [x] T035 [P] [US2] Create `backend/app/schemas/company.py` — Pydantic v2 models: `CompanyRead(id, name, name_ar, tax_registration, is_active, settings, created_at, updated_at)` with from_attributes=True. `CompanyUpdate(name: str | None = None, name_ar: str | None = None, tax_registration: str | None = None, settings: dict | None = None)` — all fields optional for partial update.

- [x] T036 [P] [US2] Create `backend/app/schemas/user.py` — Pydantic v2 models: `UserCreate(email: EmailStr, name: str, name_ar: str, password: str = Field(min_length=8), role: Literal["field_worker", "accountant", "admin"])`. `UserRead(id, email, name, name_ar, role, is_active, created_at)` — excludes hashed_password and sensitive fields. `UserUpdate(name: str | None, name_ar: str | None, role: str | None, is_active: bool | None, password: str | None = Field(None, min_length=8))`. `PaginatedUsers(items: list[UserRead], total: int, page: int, per_page: int)`.

- [x] T037 [P] [US2] Create `backend/app/schemas/project.py` — Pydantic v2 models: `ProjectCreate(name: str, name_ar: str, code: str, budget: Decimal | None = None)`. `ProjectRead(id, name, name_ar, code, budget, is_active, created_at)`. `ProjectUpdate(name: str | None, name_ar: str | None, budget: Decimal | None, is_active: bool | None)`. `PaginatedProjects(items: list[ProjectRead], total: int, page: int, per_page: int)`.

- [x] T038 [P] [US2] Create `backend/app/schemas/category.py` — Pydantic v2 models: `CategoryCreate(name: str, name_ar: str, sort_order: int = 0)`. `CategoryRead(id, name, name_ar, sort_order, is_active)`. `CategoryUpdate(name: str | None, name_ar: str | None, sort_order: int | None, is_active: bool | None)`.

- [x] T039 [US2] Create `backend/app/models/project.py` — Project model extending Base, TimestampMixin, TenantMixin. Fields per data-model.md: id String(36) PK default uuid4, name String(255) NOT NULL, name_ar String(255) NOT NULL, code String(50) NOT NULL, budget Numeric(15,2) nullable, is_active Boolean default True. Table name "projects". Add UniqueConstraint on (company_id, code) via __table_args__. Note: company_id from TenantMixin.

- [x] T040 [P] [US2] Create `backend/app/models/category.py` — Category model extending Base, TimestampMixin, TenantMixin. Fields per data-model.md: id String(36) PK default uuid4, name String(100) NOT NULL, name_ar String(100) NOT NULL, sort_order Integer default 0, is_active Boolean default True. Table name "categories". Add UniqueConstraint on (company_id, name) via __table_args__.

- [x] T041 [US2] Create `backend/app/api/v1/companies.py` — APIRouter prefix="/companies", tags=["companies"]. (1) `GET /me` — dependency require_admin, query Company by user.company_id, return CompanyRead. (2) `PATCH /me` — dependency require_admin, accept CompanyUpdate body, update only provided (non-None) fields on the admin's Company record, commit, return updated CompanyRead. Both endpoints are tenant-scoped: admin can only access their own company.

- [x] T042 [US2] Create `backend/app/api/v1/users.py` — APIRouter prefix="/users", tags=["users"]. (1) `GET /` — dependency require_admin, query params: role (optional str), is_active (optional bool), page (int default 1), per_page (int default 20). Filter by company_id from tenant scope. Apply optional role and is_active filters. Return PaginatedUsers with total count. (2) `POST /` — dependency require_admin, accept UserCreate body, check email uniqueness (global), hash password via security.hash_password, set company_id from admin's tenant scope, create User record, commit, return UserRead (201). On duplicate email: raise 409 with "البريد الإلكتروني مسجل بالفعل" / "Email already registered". (3) `PATCH /{user_id}` — dependency require_admin, query User by user_id AND company_id (tenant-scoped), if not found raise 404, update only provided fields, if password provided → hash it, commit, return UserRead.

- [x] T043 [US2] Create `backend/app/api/v1/projects.py` — APIRouter prefix="/projects", tags=["projects"]. (1) `GET /` — dependency require_admin, query params: is_active (optional bool), page, per_page. Filter by company_id. Return PaginatedProjects. (2) `POST /` — dependency require_admin, accept ProjectCreate, check (company_id, code) uniqueness, set company_id from tenant, create Project, commit, return ProjectRead (201). On duplicate code: raise 409 "كود المشروع مستخدم بالفعل" / "Project code already exists". (3) `PATCH /{project_id}` — dependency require_admin, query by project_id AND company_id, update provided fields, commit, return ProjectRead.

- [x] T044 [US2] Create `backend/app/api/v1/categories.py` — APIRouter prefix="/categories", tags=["categories"]. (1) `GET /` — dependency require_admin, query params: is_active (optional bool). Filter by company_id, order by sort_order ASC. Return list of CategoryRead (no pagination — categories are few). (2) `POST /` — dependency require_admin, accept CategoryCreate, check (company_id, name) uniqueness, set company_id, create Category, commit, return CategoryRead (201). On duplicate: raise 409 "اسم الفئة مستخدم بالفعل". (3) `PATCH /{category_id}` — dependency require_admin, query by id AND company_id, update provided fields, commit, return CategoryRead.

- [x] T045 [US2] Update `backend/app/api/v1/__init__.py` — Include all routers on v1_router: auth_router (already added in T026), companies_router, users_router, projects_router, categories_router with their respective prefixes.

- [x] T046 [US2] Generate Alembic migration for Project and Category tables — run `alembic revision --autogenerate -m "add projects and categories tables"`. Verify migration creates: projects table with UniqueConstraint(company_id, code), categories table with UniqueConstraint(company_id, name), foreign keys to companies. Run `alembic upgrade head`. Verify with `\dt` in psql.

- [x] T047 [US2] Create `backend/app/services/seed.py` — Async seed script runnable via `python -m app.services.seed`. Flow: (1) Check if company with SEED_ADMIN_EMAIL's domain exists → skip if yes (idempotent). (2) Create Company: name="ENGEZ Demo", name_ar="إنجز ديمو", is_active=True. (3) Create admin User: email from SEED_ADMIN_EMAIL, name="Admin", name_ar="المدير", password hashed from SEED_ADMIN_PASSWORD, role="admin", company_id=new company. (4) Create 8 default Categories per research R4: مواد بناء/Building Materials, نقل ومواصلات/Transportation, عمالة/Labor, طعام وشراب/Food & Beverage, معدات/Equipment, إيجار/Rent, مرافق/Utilities, متنوعة/Miscellaneous — with sort_order 0-7, company_id=new company. (5) Commit all. Print summary of what was created. Use `if __name__ == "__main__": asyncio.run(main())` pattern with async engine.

**Checkpoint**: Admin CRUD API is fully operational. Seed command creates initial data. Tenant isolation enforced: Company A's admin cannot see Company B's data.

---

## Phase 5: User Story 3 — App Works Offline After First Load (Priority: P3)

**Goal**: After one online visit, the app loads instantly from cache with no network. All fonts, locale strings, and the app shell are available offline. The app is installable as a PWA.

**Independent Test**: Load app once with network → disconnect network → reload → full app shell renders with Arabic fonts and navigation. Install as PWA from browser → launches standalone with teal theme and "إنجز" name.

### Implementation for User Story 3

- [x] T048 [US3] Create PWA icon assets — generate `frontend/public/pwa-192x192.png` (192x192 teal #0D9488 background, centered white "إنجز" text or geometric logo placeholder) and `frontend/public/pwa-512x512.png` (512x512 same design). Create `frontend/public/apple-touch-icon.png` (180x180). Create `frontend/public/favicon.ico` (multi-size favicon). These can be simple solid-color placeholders with the app initial — they will be replaced by final design assets later.

- [x] T049 [US3] Create `frontend/src/lib/db.ts` — Import Dexie and EntityTable types. Define TypeScript interfaces matching data-model.md client schema: `OfflineExpense` (id string, userId, projectId?, categoryId, amount number, currency string, category string, vendor?, vendorTaxReg?, notes?, receiptBlob?: Blob, receiptUrl?, voiceBlob?: Blob, voiceTranscript?, status: "draft"|"pending"|"synced"|"approved"|"rejected", etaUuid?, etaVerified boolean, aiExtraction?, aiConfidence?, createdAt Date, syncedAt? Date, syncError? string). `OfflineProject` (id, companyId, name, nameAr, code, budget?, isActive). `OfflineCategory` (id, companyId, name, nameAr, sortOrder, isActive). `SyncQueueItem` (id string, type: "expense"|"expense_update", payload string JSON, retryCount number, createdAt Date, lastAttempt? Date). Create Dexie instance named "EngezDB" with version(1).stores() defining indexes: expenses "id, userId, projectId, categoryId, status, createdAt, syncedAt", projects "id, companyId, code, isActive", categories "id, companyId, isActive", syncQueue "id, type, createdAt, retryCount". Export typed db instance.

- [x] T050 [US3] Create `frontend/src/lib/sync.ts` — SyncManager module: (1) `addToQueue(type, payload)` → generate UUID id, store SyncQueueItem in db.syncQueue with retryCount=0 and createdAt=now. (2) `processQueue()` → query all syncQueue items ordered by createdAt ASC, for each: parse payload JSON, call appropriate API endpoint (POST /api/v1/expenses for type "expense"), on success → delete from syncQueue, on failure → increment retryCount, set lastAttempt=now, if retryCount > 10 → set syncError on the related OfflineExpense. (3) `registerBackgroundSync()` → if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) → navigator.serviceWorker.ready.then(sw => sw.sync.register('engez-sync')). (4) `startPollingFallback()` → detect Safari/iOS via !('sync' in ServiceWorkerRegistration.prototype), if no Background Sync → setInterval(processQueue, 30000). (5) `initSync()` → register background sync + start polling fallback + add window 'online' event listener to trigger processQueue immediately on reconnect. Export initSync and addToQueue.

- [x] T051 [US3] Update `frontend/src/App.tsx` — Add useEffect on mount that calls `initSync()` from sync.ts to register background sync and start polling fallback. This ensures the sync infrastructure is active as soon as the app loads, even before any expenses are created.

**Checkpoint**: App is a fully installable PWA. After first visit, app shell loads offline with all fonts and locale strings. Dexie.js database is initialized. Sync queue infrastructure is ready for expense submissions (built in later phases).

---

## Phase 6: User Story 4 — Database Stores Expenses with Full Audit Trail (Priority: P4)

**Goal**: Complete the server-side database schema with all 7 entities. Expense, CorrectionFeedback, and VendorCache tables are created with correct relationships, constraints, and indexes.

**Independent Test**: Run Alembic migration → all 7 tables exist. Insert an expense record linked to a user, project, and category → all FKs enforce. Insert a correction feedback record → links to expense and corrector. Insert a vendor cache record → unique constraint on (company_id, tax_registration).

### Implementation for User Story 4

- [x] T052 [US4] Create `backend/app/models/expense.py` — Expense model extending Base, TimestampMixin, TenantMixin. Fields per data-model.md: id String(36) PK default uuid4, user_id String(36) FK → users.id NOT NULL, project_id String(36) FK → projects.id nullable, category_id String(36) FK → categories.id NOT NULL, amount Numeric(12,2) NOT NULL, currency String(3) NOT NULL default "EGP", vendor String(255) nullable, vendor_tax_reg String(50) nullable, notes Text nullable, receipt_url String(500) nullable, receipt_hash String(64) nullable, voice_transcript Text nullable, status String(20) NOT NULL default "pending", rejection_reason Text nullable, eta_uuid String(64) nullable, eta_verified Boolean default False, ai_extraction JSONB nullable, ai_confidence JSONB nullable, anomaly_flags JSONB nullable, synced_at DateTime(timezone=True) nullable, offline_id String(36) nullable. Table name "expenses". __table_args__: Index("ix_expenses_company_status", "company_id", "status"), Index("ix_expenses_company_project", "company_id", "project_id"), Index("ix_expenses_user_created", "user_id", "created_at").

- [x] T053 [P] [US4] Create `backend/app/models/correction.py` — CorrectionFeedback model extending Base, TimestampMixin, TenantMixin. Fields per data-model.md: id String(36) PK default uuid4, expense_id String(36) FK → expenses.id NOT NULL, field_name String(50) NOT NULL, ai_value Text NOT NULL, corrected_value Text NOT NULL, corrected_by String(36) FK → users.id NOT NULL. Table name "correction_feedback".

- [x] T054 [P] [US4] Create `backend/app/models/vendor_cache.py` — VendorCache model extending Base, TimestampMixin, TenantMixin. Fields per data-model.md: id String(36) PK default uuid4, tax_registration String(50) NOT NULL indexed, name String(255) NOT NULL, name_ar String(255) nullable, category_hint String(100) nullable. Table name "vendor_cache". __table_args__: UniqueConstraint("company_id", "tax_registration", name="uq_vendor_company_tax").

- [x] T055 [US4] Update `backend/app/models/__init__.py` — Import ALL 7 models so Alembic autogenerate discovers them: `from app.models.company import Company`, `from app.models.user import User`, `from app.models.project import Project`, `from app.models.category import Category`, `from app.models.expense import Expense`, `from app.models.correction import CorrectionFeedback`, `from app.models.vendor_cache import VendorCache`. This is critical for Alembic's `--autogenerate` to detect all tables.

- [x] T056 [US4] Generate Alembic migration for Expense, CorrectionFeedback, VendorCache — run `alembic revision --autogenerate -m "add expenses, correction_feedback, and vendor_cache tables"`. Verify migration creates all three tables with: correct FK relationships (expense → user, project, category; correction → expense, user; vendor_cache → company), composite indexes on expenses, unique constraint on vendor_cache (company_id, tax_registration). Run `alembic upgrade head`. Verify all 7 tables exist: `\dt` in psql should show companies, users, projects, categories, expenses, correction_feedback, vendor_cache.

**Checkpoint**: All 7 database entities exist with correct schema, relationships, and indexes. Full audit trail is in place. The data foundation supports all future phases (expense capture, approval, AI, reporting).

---

## Phase 7: User Story 5 — Bilingual Interface with Arabic Default (Priority: P5)

**Goal**: All interface text is available in Arabic and English. Arabic is default. User can toggle language. Layout direction flips. Amounts always render LTR.

**Independent Test**: App loads in Arabic RTL → toggle to English → all strings change, layout flips to LTR, amounts stay LTR → toggle back → Arabic RTL restored. Works offline.

### Implementation for User Story 5

- [x] T057 [US5] Create `frontend/public/locales/ar/common.json` — Complete Arabic translation file. Keys structure: `app.name` ("إنجز"), `app.tagline` ("إدارة مصروفات الميدان"). `nav.home` ("الرئيسية"), `nav.expenses` ("المصروفات"), `nav.projects` ("المشاريع"), `nav.settings` ("الإعدادات"). `expense.new` ("مصروف جديد"), `expense.amount` ("المبلغ"), `expense.category` ("الفئة"), `expense.vendor` ("المورد"), `expense.project` ("المشروع"), `expense.notes` ("ملاحظات"), `expense.submit` ("إرسال"), `expense.pending` ("في الانتظار"), `expense.approved` ("تم الموافقة"), `expense.rejected` ("مرفوض"), `expense.voice` ("تسجيل صوتي"), `expense.camera` ("صورة الإيصال"), `expense.savedLocally` ("محفوظ محلياً — سيتم المزامنة عند الاتصال"), `expense.synced` ("تمت المزامنة"), `expense.etaVerified` ("تم التحقق من الفاتورة الإلكترونية"). `auth.login` ("تسجيل الدخول"), `auth.email` ("البريد الإلكتروني"), `auth.password` ("كلمة المرور"), `auth.logout` ("تسجيل الخروج"), `auth.invalidCredentials` ("البريد الإلكتروني أو كلمة المرور غير صحيحة"), `auth.accountLocked` ("تم تأمين الحساب. حاول مرة أخرى بعد 15 دقيقة"), `auth.biometric` ("تسجيل الدخول بالبصمة"). `status.online` ("متصل"), `status.offline` ("غير متصل"), `status.syncing` ("جاري المزامنة..."). `roles.field_worker` ("عامل ميدان"), `roles.accountant` ("محاسب"), `roles.admin` ("مدير"). `admin.users` ("المستخدمون"), `admin.companies` ("الشركات"), `admin.projects` ("المشاريع"), `admin.categories` ("الفئات"), `admin.create` ("إنشاء"), `admin.edit` ("تعديل"). `common.save` ("حفظ"), `common.cancel` ("إلغاء"), `common.confirm` ("تأكيد"), `common.back` ("رجوع"), `common.search` ("بحث"), `common.filter` ("تصفية"), `common.noResults` ("لا توجد نتائج"), `common.loading` ("جاري التحميل..."), `common.error` ("حدث خطأ"), `common.retry` ("إعادة المحاولة"), `common.delete` ("حذف"). `validation.required` ("هذا الحقل مطلوب"), `validation.invalidEmail` ("بريد إلكتروني غير صالح"), `validation.minLength` ("يجب أن يكون {{count}} أحرف على الأقل"). `language.toggle` ("English"), `language.current` ("العربية").

- [x] T058 [P] [US5] Create `frontend/public/locales/en/common.json` — Complete English mirror with identical key structure: `app.name` ("ENGEZ"), `app.tagline` ("Field Expense Management"), `nav.home` ("Home"), `nav.expenses` ("Expenses"), `nav.projects` ("Projects"), `nav.settings` ("Settings"), all expense/auth/status/roles/admin/common/validation keys in English. `language.toggle` ("العربية"), `language.current` ("English"). Every key in ar/common.json MUST have a corresponding key in en/common.json.

- [x] T059 [US5] Create `frontend/src/lib/i18n.ts` — Import i18n from 'i18next', initReactI18next from 'react-i18next', LanguageDetector from 'i18next-browser-languagedetector'. Import arCommon from JSON (static import for offline-first: `import arCommon from '../../public/locales/ar/common.json'`), import enCommon similarly. Configure: .use(LanguageDetector).use(initReactI18next).init({ fallbackLng: 'ar', defaultNS: 'common', ns: ['common'], interpolation: { escapeValue: false }, detection: { order: ['localStorage', 'navigator'], caches: ['localStorage'], lookupLocalStorage: 'engez-lang' }, resources: { ar: { common: arCommon }, en: { common: enCommon } } }). Export i18n. Note: static imports ensure translations are bundled and available offline without network fetch.

- [x] T060 [US5] Create `frontend/src/hooks/useDirection.ts` — Custom hook: import useTranslation from react-i18next. Get current language via i18n.language. Compute dir: 'ar' → 'rtl', 'en' → 'ltr'. Use useEffect to set `document.documentElement.dir = dir` and `document.documentElement.lang = language` whenever language changes. Return `{ dir: 'rtl' | 'ltr', isRTL: boolean, language: string }`.

- [x] T061 [US5] Update `frontend/src/pages/Login.tsx` — Replace ALL hardcoded Arabic text with t() calls: heading → t('app.name'), subtitle → t('app.tagline'), email label → t('auth.email'), password label → t('auth.password'), submit button → t('auth.login'), error messages → t('auth.invalidCredentials') and t('auth.accountLocked'). Add language toggle button in top corner: shows t('language.toggle'), on click calls i18n.changeLanguage(current === 'ar' ? 'en' : 'ar'). Ensure form still works identically in both languages.

- [x] T062 [US5] Update `frontend/src/pages/Home.tsx` — Replace ALL hardcoded text with t() calls: welcome message uses t() with user.name_ar or user.name based on current language, company name similarly. Role badge text → t(`roles.${user.role}`). "New expense" button → t('expense.new'). Online/offline indicator → t('status.online') / t('status.offline'). Amounts rendered with `.amount-display` CSS class to ensure LTR direction with tabular-nums regardless of language. Add language toggle accessible from home screen.

- [x] T063 [US5] Update `frontend/src/App.tsx` — Integrate useDirection hook at App root level so document direction updates on every language change. Ensure the direction change triggers re-render of layout-sensitive components. Verify that toggling language while offline works instantly (since all locale files are statically imported).

**Checkpoint**: All user stories complete. Full bilingual interface, Arabic default, instant offline language toggle, LTR amounts.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and cross-cutting improvements.

- [x] T064 Run frontend build verification — execute `cd frontend && pnpm build`. Must complete with zero TypeScript errors and zero build warnings. Fix any issues found. Verify dist/ output includes service worker (sw.js), manifest (manifest.webmanifest), and all precached assets.

- [x] T065 Run backend startup verification — execute `docker compose up -d --build` (rebuild to include all new code). Verify all services healthy via `docker compose ps`. Run `docker compose exec api alembic upgrade head` — must apply all migrations cleanly. Run `docker compose exec api python -m app.services.seed` — must create demo company + admin + categories. Test `curl http://localhost:8000/health` returns OK. Test `curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@engez.app","password":"changeme123"}'` returns access_token.

- [x] T066 [P] Verify tenant isolation — using curl or httpx: create two test companies (via seed or directly), create users in each, authenticate as user in Company A, call GET /users → should return only Company A users. Authenticate as Company B user, call GET /users → should return only Company B users. Zero cross-tenant leakage.

- [x] T067 [P] Verify PWA installability — open http://localhost:5173 in Chrome. Open DevTools > Application tab. Verify: (1) Manifest section shows "إنجز" name, teal theme, RTL direction, icons detected. (2) Service Workers section shows worker registered and active. (3) "Installability" shows no errors (or only HTTPS warning expected in dev). (4) IndexedDB shows "EngezDB" with tables: expenses, projects, categories, syncQueue.

- [x] T068 [P] Verify offline functionality — in Chrome DevTools: (1) Load app fully. (2) Go to Network tab → check "Offline". (3) Reload page → app shell loads from service worker cache, Arabic fonts render, navigation works. (4) Uncheck "Offline" → app reconnects.

- [x] T069 Run `specs/001-phase1-foundation/quickstart.md` validation — follow every step in the quickstart guide from scratch: clone, .env setup, docker compose up, migrations, seed, frontend install, pnpm dev, verify all 5 checkpoints described in quickstart.md. Fix any step that doesn't work.

- [x] T070 Final cleanup — verify no leftover boilerplate files from Vite template, no console.log statements in production code, no hardcoded secrets, no TODO comments for Phase 1 scope items. Ensure .env.example files are complete and accurate. Verify git status is clean (all new files tracked, nothing accidentally committed that shouldn't be).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start after Foundational — no dependency on other stories
  - US2 (Phase 4): Depends on US1 (needs auth router setup in T026)
  - US3 (Phase 5): Can start after Foundational — independent of US1/US2 backend work
  - US4 (Phase 6): Can start after Foundational — independent backend models only
  - US5 (Phase 7): Depends on US1 (needs Login.tsx and Home.tsx to exist for i18n integration)
- **Polish (Phase 8)**: Depends on all user stories being complete

### Within Each User Story

- Schemas before services
- Models before migrations
- Services before endpoints
- Backend before frontend (for API contract fulfillment)
- Core implementation before integration touches

### Parallel Opportunities

**Within Phase 1 (Setup)**:
- T003, T004, T005, T006, T007 can all run in parallel (different files, zero overlap)
- T009, T010, T011 can run in parallel after T001

**Within Phase 2 (Foundational)**:
- T016 (Company model) can run in parallel once T015 (base.py) is done

**Within Phase 4 (US2)**:
- T035, T036, T037, T038 can all run in parallel (separate schema files)
- T039, T040 can run in parallel (separate model files)

**Within Phase 6 (US4)**:
- T053, T054 can run in parallel (separate model files)

**Within Phase 7 (US5)**:
- T057, T058 can run in parallel (separate locale files)

**Within Phase 8 (Polish)**:
- T066, T067, T068 can all run in parallel (independent verification)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Login + Home)
4. **STOP and VALIDATE**: Login works, Arabic RTL, dark mode, session persistence
5. This is a shippable MVP — a user can log in and see the app

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Login/Home) → Test independently → **MVP!**
3. Add US2 (Admin CRUD) → Test independently → Admin can manage users
4. Add US3 (PWA/Offline) → Test independently → App works offline
5. Add US4 (Full Schema) → Test independently → All tables ready for Phase 2
6. Add US5 (i18n) → Test independently → Full bilingual interface
7. Polish → Final validation → **Phase 1 Complete**
8. Proceed to `02_PHASE2_CORE_CAPTURE.md`

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths are relative to project root (`C:\apps\engez`)
- Backend paths assume backend/ prefix, frontend paths assume frontend/ prefix
- Arabic strings in task descriptions are the actual values to use, not placeholders
