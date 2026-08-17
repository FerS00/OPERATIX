"""Command-line interface for Step 1."""

from __future__ import annotations

import argparse

from operatix.application.repositories import build_repository
from operatix.application.sales_agent import SalesAgent
from operatix.config import Settings, load_local_env
from operatix.llm.providers import Provider, build_chat_model, friendly_provider_error


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Registra ventas con OPERATIX.")
    result.add_argument("message", help="Pedido en lenguaje natural.")
    result.add_argument("--provider", choices=[item.value for item in Provider], default="openai")
    result.add_argument("--model", help="Modelo del proveedor; reemplaza la configuración.")
    result.add_argument("--backend", choices=["excel", "google_sheets"])
    result.add_argument("--excel-path", help="Ruta del libro Excel local.")
    result.add_argument("--spreadsheet-id", help="ID de Google Sheets.")
    result.add_argument("--credentials", help="JSON de cuenta de servicio de Google.")
    result.add_argument("--worksheet", default="Ventas")
    return result


def main() -> None:
    load_local_env()
    args = parser().parse_args()
    try:
        settings = Settings.from_env()
        repository = build_repository(
            settings,
            backend=args.backend,
            excel_path=args.excel_path,
            spreadsheet_id=args.spreadsheet_id,
            credentials_path=args.credentials,
            worksheet=args.worksheet,
        )
        model = build_chat_model(args.provider, args.model)
        outcome = SalesAgent(model, repository).process(args.message)
        print(outcome.message)
    except Exception as error:
        raise SystemExit(f"OPERATIX: {friendly_provider_error(error)}") from None
