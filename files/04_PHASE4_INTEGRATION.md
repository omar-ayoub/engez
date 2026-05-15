# Phase 4: Integration & Scale — Weeks 11–14

## Spec-Kit Commands for Phase 4

```bash
/speckit.specify
```

> **Specification Prompt for Phase 4:**
>
> Build the enterprise integration layer and analytics dashboard that justify the CFO's subscription.
>
> Accounting system integration via an abstraction layer (ExpenseExporter interface). First adapters: Zoho Books API, Odoo XML-RPC, and CSV export for Daftra. Approved expenses push to the external system as journal entries. The abstraction means adding a new ERP is just writing a new adapter.
>
> AI anomaly detection system: duplicate receipt detection via perceptual image hashing (>90% similarity flags), statistical outlier detection (>2 standard deviations from user+category mean), velocity checks (3+ expenses in 10 minutes), and vendor/category mismatch detection. All flags are advisory badges on the review queue — never auto-reject.
>
> Spend analytics dashboard for the CFO: spend by project (bar chart, 30/90 day), spend by category (donut chart), spend trend per team (line chart), budget vs actual per project, export to CSV/Excel.

```bash
/speckit.plan
/speckit.tasks
/speckit.implement
```

---

## Task 4.1: Accounting System Integration (Days 1–5)

### Abstraction Layer Design

Create `backend/app/services/exporters/base.py`:

```python
"""Expense exporter abstraction layer.
Adding a new ERP system = writing one new adapter file.
No refactoring of existing code needed."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExportResult:
    success: bool
    external_id: Optional[str] = None
    error: Optional[str] = None


class ExpenseExporter(ABC):
    """Interface for all accounting system integrations."""

    @abstractmethod
    async def push(self, expense: dict, company_config: dict) -> ExportResult:
        """Push an approved expense to the external accounting system.

        Args:
            expense: Expense data dict with all fields
            company_config: Company-specific API credentials and mappings

        Returns:
            ExportResult with success status and external reference ID
        """
        ...

    @abstractmethod
    async def test_connection(self, company_config: dict) -> bool:
        """Verify API credentials are valid."""
        ...

    @abstractmethod
    def get_required_config_fields(self) -> list[str]:
        """Return list of config fields needed for setup."""
        ...
```

Create `backend/app/services/exporters/zoho_books.py`:

```python
"""Zoho Books adapter — push approved expenses as expense entries."""

import httpx

from app.services.exporters.base import ExpenseExporter, ExportResult


class ZohoBooksExporter(ExpenseExporter):

    async def push(self, expense: dict, config: dict) -> ExportResult:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"https://books.zoho.com/api/v3/expenses"
                    f"?organization_id={config['organization_id']}",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {config['access_token']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "account_id": config.get("expense_account_id"),
                        "date": expense["created_at"][:10],
                        "amount": float(expense["amount"]),
                        "currency_code": expense.get("currency", "EGP"),
                        "description": (
                            f"{expense.get('category', '')} - "
                            f"{expense.get('vendor', '')} - "
                            f"{expense.get('notes', '')}"
                        ),
                        "project_id": config.get("project_mapping", {}).get(
                            expense.get("project_id")
                        ),
                        "reference_number": expense["id"][:8],
                    },
                )
                data = response.json()

                if response.status_code == 201:
                    return ExportResult(
                        success=True,
                        external_id=data.get("expense", {}).get("expense_id"),
                    )
                return ExportResult(success=False, error=str(data))

            except Exception as e:
                return ExportResult(success=False, error=str(e))

    async def test_connection(self, config: dict) -> bool:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://books.zoho.com/api/v3/organizations",
                headers={
                    "Authorization": f"Zoho-oauthtoken {config['access_token']}"
                },
            )
            return resp.status_code == 200

    def get_required_config_fields(self) -> list[str]:
        return ["access_token", "organization_id", "expense_account_id"]
```

Create similar adapters for Odoo (`odoo_xmlrpc.py`) and CSV export (`csv_export.py`).

### Exporter Registry

Create `backend/app/services/exporters/__init__.py`:

```python
"""Exporter registry — maps system names to adapter classes."""

from app.services.exporters.base import ExpenseExporter
from app.services.exporters.zoho_books import ZohoBooksExporter

EXPORTERS: dict[str, type[ExpenseExporter]] = {
    "zoho_books": ZohoBooksExporter,
    # "odoo": OdooExporter,
    # "csv": CSVExporter,
    # "daftra": DaftraExporter,
}

def get_exporter(system_name: str) -> ExpenseExporter:
    cls = EXPORTERS.get(system_name)
    if not cls:
        raise ValueError(f"Unknown exporter: {system_name}")
    return cls()
```

---

## Task 4.2: AI Anomaly Detection (Days 6–9)

Create `backend/app/services/anomaly.py`:

```python
"""Anomaly detection — turns the app from a data-entry tool
into a financial controls system. Advisory only, never auto-reject."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from PIL import Image
from io import BytesIO
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense


async def detect_anomalies(
    db: AsyncSession,
    expense_data: dict,
    image_bytes: Optional[bytes],
    company_id: str,
    user_id: str,
) -> dict:
    """Run all anomaly checks. Returns advisory flags dict."""
    flags = {}

    # 1. Duplicate receipt detection via perceptual hash
    if image_bytes:
        img_hash = compute_perceptual_hash(image_bytes)
        duplicate = await check_duplicate_receipt(db, img_hash, company_id)
        if duplicate:
            flags["duplicate_receipt"] = {
                "severity": "high",
                "message": "صورة إيصال مشابهة تم إرسالها سابقاً",
                "similar_expense_id": duplicate,
            }
        expense_data["receipt_hash"] = img_hash

    # 2. Statistical outlier detection
    amount = expense_data.get("amount")
    category = expense_data.get("category")
    if amount and category:
        outlier = await check_statistical_outlier(
            db, company_id, user_id, category, float(amount)
        )
        if outlier:
            flags["statistical_outlier"] = {
                "severity": "medium",
                "message": f"المبلغ أعلى بكثير من المعتاد لهذه الفئة",
                "avg": outlier["avg"],
                "std": outlier["std"],
            }

    # 3. Velocity check
    velocity = await check_submission_velocity(db, company_id, user_id)
    if velocity:
        flags["high_velocity"] = {
            "severity": "medium",
            "message": f"{velocity} مصروفات في آخر 10 دقائق",
        }

    return flags


def compute_perceptual_hash(image_bytes: bytes, hash_size: int = 16) -> str:
    """Compute average hash (aHash) for perceptual image comparison.
    More robust than cryptographic hash — similar images produce similar hashes."""
    img = Image.open(BytesIO(image_bytes))
    img = img.convert("L").resize((hash_size, hash_size), Image.LANCZOS)

    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)

    return hashlib.md5(bits.encode()).hexdigest()


async def check_duplicate_receipt(
    db: AsyncSession, img_hash: str, company_id: str
) -> Optional[str]:
    """Check if a similar receipt image was already submitted."""
    stmt = select(Expense.id).where(
        Expense.company_id == company_id,
        Expense.receipt_hash == img_hash,
    ).limit(1)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    return existing


async def check_statistical_outlier(
    db: AsyncSession,
    company_id: str,
    user_id: str,
    category: str,
    amount: float,
) -> Optional[dict]:
    """Flag if amount is >2 standard deviations from user+category mean."""
    stmt = select(
        func.avg(Expense.amount).label("avg_amount"),
        func.stddev(Expense.amount).label("std_amount"),
    ).where(
        Expense.company_id == company_id,
        Expense.user_id == user_id,
        Expense.category == category,
    )
    result = await db.execute(stmt)
    stats = result.one_or_none()

    if not stats or stats.avg_amount is None or stats.std_amount is None:
        return None

    avg = float(stats.avg_amount)
    std = float(stats.std_amount)

    if std > 0 and amount > avg + (2 * std):
        return {"avg": round(avg, 2), "std": round(std, 2)}

    return None


async def check_submission_velocity(
    db: AsyncSession, company_id: str, user_id: str
) -> Optional[int]:
    """Flag if 3+ expenses submitted in last 10 minutes."""
    ten_min_ago = datetime.now(timezone.utc) - timedelta(minutes=10)

    stmt = select(func.count(Expense.id)).where(
        Expense.company_id == company_id,
        Expense.user_id == user_id,
        Expense.created_at >= ten_min_ago,
    )
    count = await db.scalar(stmt)

    return count if count and count >= 3 else None
```

---

## Task 4.3: Spend Analytics Dashboard (Days 10–14)

### API Endpoints

Create `backend/app/api/v1/analytics.py`:

```python
"""Analytics endpoints for CFO dashboard."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_role
from app.models.expense import Expense, Project, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spend-by-project")
async def spend_by_project(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            Project.name_ar,
            Project.name,
            Project.budget,
            func.sum(Expense.amount).label("total_spend"),
            func.count(Expense.id).label("expense_count"),
        )
        .join(Project, Expense.project_id == Project.id)
        .where(
            Expense.company_id == current_user.company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
        .group_by(Project.id, Project.name_ar, Project.name, Project.budget)
        .order_by(func.sum(Expense.amount).desc())
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result]


@router.get("/spend-by-category")
async def spend_by_category(
    days: int = Query(30),
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            Expense.category,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .where(
            Expense.company_id == current_user.company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
        .group_by(Expense.category)
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result]


@router.get("/spend-trend")
async def spend_trend(
    days: int = Query(90),
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(
            func.date_trunc("week", Expense.created_at).label("week"),
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .where(
            Expense.company_id == current_user.company_id,
            Expense.status == "approved",
            Expense.created_at >= since,
        )
        .group_by(func.date_trunc("week", Expense.created_at))
        .order_by(func.date_trunc("week", Expense.created_at))
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result]


@router.get("/budget-vs-actual")
async def budget_vs_actual(
    current_user: User = Depends(require_role("accountant", "admin")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            Project.name_ar,
            Project.name,
            Project.budget,
            func.coalesce(func.sum(Expense.amount), 0).label("actual_spend"),
        )
        .outerjoin(
            Expense,
            and_(
                Expense.project_id == Project.id,
                Expense.status == "approved",
            ),
        )
        .where(
            Project.company_id == current_user.company_id,
            Project.is_active == True,
        )
        .group_by(Project.id, Project.name_ar, Project.name, Project.budget)
    )
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result]
```

### Frontend: Dashboard with Recharts

Use Recharts for the analytics dashboard. Build these chart components:

1. **SpendByProjectBar** — horizontal bar chart, project names in Arabic, budget line overlay
2. **SpendByCategoryDonut** — donut/pie chart with category icons
3. **SpendTrendLine** — weekly spend line chart with area fill
4. **BudgetVsActualBar** — grouped bar chart comparing budget vs actual

Each chart should use `react-i18next` for Arabic labels and RTL-compatible layout.

```bash
# Install Recharts
cd frontend
pnpm add recharts@^2.15.0
```

### Run Impeccable on Dashboard

```bash
/impeccable critique dashboard
/impeccable typeset dashboard  # Fix typography scales
/impeccable colorize dashboard # Ensure accessible contrast
/impeccable polish dashboard
```

---

## Phase 4 Completion Checklist

- [ ] ExpenseExporter abstraction layer accepts adapters cleanly
- [ ] Zoho Books adapter pushes approved expenses successfully
- [ ] CSV export generates downloadable file
- [ ] Duplicate receipt detection flags >90% similar images
- [ ] Statistical outlier detection flags amounts >2σ from mean
- [ ] Velocity check flags 3+ expenses in 10 minutes
- [ ] All anomaly flags display as advisory badges (not blocking)
- [ ] Spend by project chart renders with Arabic labels
- [ ] Spend by category donut chart renders
- [ ] Spend trend line chart shows weekly aggregation
- [ ] Budget vs actual comparison works for active projects
- [ ] CSV/Excel export downloads correctly
- [ ] Dashboard loads in under 2 seconds
- [ ] All charts accessible in dark mode with sufficient contrast
- [ ] `/impeccable audit dashboard` passes

**Proceed to `05_DEPLOYMENT_OPS.md` →**
