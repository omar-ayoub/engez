from sqlalchemy import select

from app.core.tenant import TenantScope
from app.models.expense import Expense
from app.models.company import Company


def test_query_adds_company_filter_for_tenant_model():
    scope = TenantScope("comp-001")
    stmt = scope.query(Expense)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "company_id" in sql
    assert "comp-001" in sql


def test_query_skips_filter_for_non_tenant_model():
    scope = TenantScope("comp-001")
    stmt = scope.query(Company)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "comp-001" not in sql


def test_filter_adds_company_to_existing_statement():
    scope = TenantScope("comp-002")
    base_stmt = select(Expense).where(Expense.status == "pending")
    filtered = scope.filter(base_stmt, Expense)
    sql = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert "comp-002" in sql
    assert "pending" in sql


def test_filter_passes_through_for_non_tenant_model():
    scope = TenantScope("comp-002")
    base_stmt = select(Company)
    filtered = scope.filter(base_stmt, Company)
    sql = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert "comp-002" not in sql


def test_str_returns_company_id():
    scope = TenantScope("comp-xyz")
    assert str(scope) == "comp-xyz"
    assert scope.company_id == "comp-xyz"
