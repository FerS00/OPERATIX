"""LangGraph-backed sales registration use case."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from langchain.agents import create_agent
from langchain.tools import BaseTool, tool
from langchain_core.language_models.chat_models import BaseChatModel

from operatix.domain.sales import SaleCommand, SaleRecord
from operatix.ports.sales_repository import SalesRepository

SYSTEM_PROMPT = """
Eres el agente transaccional de OPERATIX. Tu responsabilidad en este paso es registrar ventas.

Reglas:
1. Cuando el usuario pida agregar o registrar una venta y estén presentes cliente, producto,
   cantidad e importe, llama exactamente una vez a la herramienta register_sale.
2. Interpreta un importe como total salvo que el usuario diga claramente "cada uno",
   "por unidad", "precio unitario" o equivalente.
3. Usa USD para el símbolo $ y PEN para S/. salvo que el usuario indique otra moneda.
4. No inventes datos obligatorios. Si falta alguno, pide únicamente el dato faltante y no llames
   a la herramienta.
5. Después de una escritura exitosa, confirma los campos principales y el ID de transacción.
""".strip()


@dataclass(slots=True)
class ToolExecution:
    sale: SaleRecord | None = None
    inserted: bool = False


@dataclass(frozen=True, slots=True)
class AgentOutcome:
    message: str
    sale: SaleRecord | None
    inserted: bool


def build_register_sale_tool(
    repository: SalesRepository,
    transaction_id: UUID | None = None,
) -> tuple[BaseTool, ToolExecution]:
    """Create an idempotent tool bound to one application request."""
    request_id = transaction_id or uuid4()
    execution = ToolExecution()

    @tool("register_sale", args_schema=SaleCommand)
    def register_sale(
        customer_name: str,
        product: str,
        quantity: int,
        amount: Decimal,
        price_basis: Literal["total", "unit"] = "total",
        currency: str = "USD",
        notes: str | None = None,
    ) -> dict[str, object]:
        """Registra una venta estructurada en el sistema transaccional seleccionado."""
        command = SaleCommand(
            customer_name=customer_name,
            product=product,
            quantity=quantity,
            amount=amount,
            price_basis=price_basis,
            currency=currency,
            notes=notes,
        )
        sale = SaleRecord.from_command(command, transaction_id=request_id)
        execution.sale = sale
        execution.inserted = repository.append(sale)
        return {
            "status": "inserted" if execution.inserted else "already_exists",
            "transaction": sale.model_dump(mode="json"),
        }

    return register_sale, execution


def _message_text(message: object) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


class SalesAgent:
    """Small agent facade; LangChain's create_agent runs on LangGraph."""

    def __init__(self, model: BaseChatModel, repository: SalesRepository) -> None:
        self.model = model
        self.repository = repository

    def process(self, user_text: str) -> AgentOutcome:
        if not user_text.strip():
            raise ValueError("El mensaje no puede estar vacío.")

        register_sale, execution = build_register_sale_tool(self.repository)
        graph = create_agent(
            model=self.model,
            tools=[register_sale],
            system_prompt=SYSTEM_PROMPT,
        )
        result = graph.invoke({"messages": [{"role": "user", "content": user_text}]})
        final_message = _message_text(result["messages"][-1])
        return AgentOutcome(
            message=final_message,
            sale=execution.sale,
            inserted=execution.inserted,
        )
