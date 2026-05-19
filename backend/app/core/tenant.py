from sqlalchemy import Select, select

from app.models.base import TenantMixin


class TenantScope:
    def __init__(self, company_id: str):
        self.company_id = company_id

    def query(self, *entities) -> Select:
        stmt = select(*entities)
        for entity in entities:
            model = entity if isinstance(entity, type) else getattr(entity, "class_", None)
            if model and issubclass(model, TenantMixin):
                stmt = stmt.where(model.company_id == self.company_id)
        return stmt

    def filter(self, stmt: Select, model: type) -> Select:
        if issubclass(model, TenantMixin):
            return stmt.where(model.company_id == self.company_id)
        return stmt

    def __str__(self) -> str:
        return self.company_id
