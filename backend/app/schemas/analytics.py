from pydantic import BaseModel


class SpendByProject(BaseModel):
    name: str
    name_ar: str
    budget: float | None
    total_spend: float
    expense_count: int


class SpendByCategory(BaseModel):
    category: str
    category_ar: str
    total: float
    count: int


class SpendTrend(BaseModel):
    week: str
    total: float
    count: int


class BudgetVsActual(BaseModel):
    name: str
    name_ar: str
    budget: float | None
    actual_spend: float


class AnalyticsSummary(BaseModel):
    total_spend: float
    expense_count: int
    project_count: int
    period_days: int


class ExportParams(BaseModel):
    format: str
    view: str
    days: int = 30
