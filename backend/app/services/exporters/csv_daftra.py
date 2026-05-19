import csv
import io
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.services.exporters.base import ExpenseExporter

logger = logging.getLogger(__name__)


class CsvDaftraExporter(ExpenseExporter):
    async def push(self, db: AsyncSession, expense_id: str, company_id: str) -> str:
        raise NotImplementedError("CSV Daftra uses date-range export, not single expense push")

    async def test_connection(self, credentials: dict) -> tuple[bool, str]:
        return True, "CSV export requires no connection"

    def get_required_config_fields(self) -> list[str]:
        return []

    @staticmethod
    async def generate_csv(
        db: AsyncSession,
        company_id: str,
        date_from: datetime,
        date_to: datetime,
    ) -> str:
        query = (
            select(Expense)
            .where(
                Expense.company_id == company_id,
                Expense.status == "approved",
                Expense.created_at >= date_from,
                Expense.created_at <= date_to,
            )
            .order_by(Expense.created_at)
        )
        result = await db.execute(query)
        expenses = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "التاريخ", "المبلغ", "العملة", "المورد", "البند", "الفئة",
            "المشروع", "ملاحظات", "الحالة",
        ])

        for exp in expenses:
            writer.writerow([
                exp.created_at.strftime("%Y-%m-%d") if exp.created_at else "",
                f"{float(exp.amount):.2f}",
                exp.currency,
                exp.vendor or "",
                exp.items or "",
                exp.category_id or "",
                exp.project_id or "",
                exp.notes or "",
                exp.status,
            ])

        return output.getvalue()
