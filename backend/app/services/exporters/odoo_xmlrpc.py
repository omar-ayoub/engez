import json
import logging
import xmlrpc.client


from app.services.exporters.base import ExpenseExporter
from app.services.crypto import decrypt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.expense import Expense
from app.models.integration import IntegrationConfig

logger = logging.getLogger(__name__)


class OdooXmlRpcExporter(ExpenseExporter):
    async def push(self, db: AsyncSession, expense_id: str, company_id: str) -> str:
        result = await db.execute(
            select(Expense).where(Expense.id == expense_id, Expense.company_id == company_id)
        )
        expense = result.scalar_one()
        config_result = await db.execute(
            select(IntegrationConfig).where(IntegrationConfig.company_id == company_id)
        )
        config = config_result.scalar_one()
        creds = json.loads(decrypt(company_id, config.encrypted_credentials))

        url = creds["url"]
        db_name = creds["database"]
        uid = creds["uid"]
        password = creds["password"]

        import asyncio
        loop = asyncio.get_running_loop()
        ref_id = await loop.run_in_executor(
            None,
            self._create_journal_entry,
            url, db_name, uid, password, expense,
        )
        return str(ref_id)

    def _create_journal_entry(self, url: str, db_name: str, uid: int, password: str, expense) -> int:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        journal_id = models.execute_kw(
            db_name, uid, password,
            "account.journal", "search",
            [[["type", "=", "purchase"]]],
            {"limit": 1},
        )
        if not journal_id:
            raise Exception("No purchase journal found in Odoo")

        entry_vals = {
            "journal_id": journal_id[0],
            "date": expense.created_at.strftime("%Y-%m-%d"),
            "ref": expense.id,
            "line_ids": [
                (0, 0, {
                    "name": expense.items or "Expense",
                    "debit": float(expense.amount),
                    "account_id": self._get_expense_account(models, db_name, uid, password),
                }),
                (0, 0, {
                    "name": expense.items or "Expense",
                    "credit": float(expense.amount),
                    "account_id": self._get_payable_account(models, db_name, uid, password),
                }),
            ],
        }
        return models.execute_kw(
            db_name, uid, password,
            "account.move", "create",
            [entry_vals],
        )

    def _get_expense_account(self, models, db_name, uid, password) -> int:
        accounts = models.execute_kw(
            db_name, uid, password,
            "account.account", "search",
            [[["account_type", "=", "expense"]]],
            {"limit": 1},
        )
        return accounts[0] if accounts else 1

    def _get_payable_account(self, models, db_name, uid, password) -> int:
        accounts = models.execute_kw(
            db_name, uid, password,
            "account.account", "search",
            [[["account_type", "=", "account_payable"]]],
            {"limit": 1},
        )
        return accounts[0] if accounts else 1

    async def test_connection(self, credentials: dict) -> tuple[bool, str]:
        url = credentials.get("url", "")
        db_name = credentials.get("database", "")
        uid_val = credentials.get("uid", 0)
        password = credentials.get("password", "")

        import asyncio
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                self._test_auth, url, db_name, uid_val, password,
            )
            return result
        except Exception as exc:
            return False, str(exc)

    def _test_auth(self, url: str, db_name: str, uid: int, password: str) -> tuple[bool, str]:
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        models.execute_kw(
            db_name, uid, password,
            "res.users", "search_count",
            [[["id", "=", uid]]],
        )
        return True, "Connection successful"

    def get_required_config_fields(self) -> list[str]:
        return ["url", "database", "uid", "password"]
