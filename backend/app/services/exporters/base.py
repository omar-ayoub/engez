from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class ExpenseExporter(ABC):
    @abstractmethod
    async def push(self, db: AsyncSession, expense_id: str, company_id: str) -> str:
        ...

    @abstractmethod
    async def test_connection(self, credentials: dict) -> tuple[bool, str]:
        ...

    @abstractmethod
    def get_required_config_fields(self) -> list[str]:
        ...
