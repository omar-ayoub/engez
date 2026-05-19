from app.services.exporters.base import ExpenseExporter
from app.services.exporters.zoho_books import ZohoBooksExporter
from app.services.exporters.odoo_xmlrpc import OdooXmlRpcExporter
from app.services.exporters.csv_daftra import CsvDaftraExporter

EXPORTERS: dict[str, type[ExpenseExporter]] = {
    "zoho_books": ZohoBooksExporter,
    "odoo": OdooXmlRpcExporter,
    "csv_daftra": CsvDaftraExporter,
}


def get_exporter(system_name: str) -> ExpenseExporter | None:
    cls = EXPORTERS.get(system_name)
    if cls is None:
        return None
    return cls()
