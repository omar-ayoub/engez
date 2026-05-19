import json
import logging

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.integration import IntegrationConfig
from app.services.exporters.base import ExpenseExporter
from app.services.crypto import decrypt

logger = logging.getLogger(__name__)


class ZohoBooksExporter(ExpenseExporter):
    API_BASE = "https://www.zohoapis.com/books/v3"

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

        access_token = creds["access_token"]
        org_id = creds["organization_id"]
        account_id = creds.get("expense_account_id", "")

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.API_BASE}/expenses?organization_id={org_id}",
                headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
                json={
                    "date": expense.created_at.strftime("%Y-%m-%d"),
                    "amount": float(expense.amount),
                    "account_id": account_id,
                    "description": expense.items or "",
                    "reference_number": expense.id,
                    "currency_code": expense.currency,
                },
            )

        if resp.status_code == 401 and config.oauth_refresh_token:
            access_token = await self._refresh_token(db, config, company_id)
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.API_BASE}/expenses?organization_id={org_id}",
                    headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
                    json={
                        "date": expense.created_at.strftime("%Y-%m-%d"),
                        "amount": float(expense.amount),
                        "account_id": account_id,
                        "description": expense.items or "",
                        "reference_number": expense.id,
                        "currency_code": expense.currency,
                    },
                )

        if resp.status_code in (200, 201):
            data = resp.json()
            return str(data.get("expense", {}).get("expense_id", ""))
        raise Exception(f"Zoho push failed: {resp.status_code} {resp.text}")

    async def _refresh_token(self, db: AsyncSession, config, company_id: str) -> str:
        creds = json.loads(decrypt(company_id, config.encrypted_credentials))
        refresh_token = decrypt(company_id, config.oauth_refresh_token) if config.oauth_refresh_token else ""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://accounts.zoho.com/oauth/v2/token",
                data={
                    "refresh_token": refresh_token,
                    "client_id": creds.get("client_id", ""),
                    "client_secret": creds.get("client_secret", ""),
                    "grant_type": "refresh_token",
                },
            )
        if resp.status_code == 200:
            new_token = resp.json().get("access_token", "")
            creds["access_token"] = new_token
            from app.services.crypto import encrypt
            config.encrypted_credentials = encrypt(company_id, json.dumps(creds))
            await db.commit()
            return new_token
        raise Exception("Token refresh failed")

    async def test_connection(self, credentials: dict) -> tuple[bool, str]:
        access_token = credentials.get("access_token", "")
        org_id = credentials.get("organization_id", "")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.API_BASE}/expenses?organization_id={org_id}",
                headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
            )
        if resp.status_code == 200:
            return True, "Connection successful"
        if resp.status_code == 401:
            return False, "Invalid access token"
        return False, f"Error: {resp.status_code}"

    def get_required_config_fields(self) -> list[str]:
        return ["access_token", "organization_id", "expense_account_id"]
