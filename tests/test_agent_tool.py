from decimal import Decimal
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from operatix.application.sales_agent import SalesAgent, build_register_sale_tool
from operatix.infrastructure.excel_repository import ExcelSalesRepository


class ToolCallingFakeModel(BaseChatModel):
    """Minimal offline model that performs one tool call and then confirms it."""

    _calls: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "operatix-test-model"

    def bind_tools(self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any):
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self._calls += 1
        if any(isinstance(message, ToolMessage) for message in messages):
            response = AIMessage(content="Venta registrada correctamente.")
        else:
            response = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "register_sale",
                        "args": {
                            "customer_name": "Juan Perez",
                            "product": "laptop",
                            "quantity": 5,
                            "amount": "2500",
                            "price_basis": "total",
                            "currency": "USD",
                        },
                        "id": "call-operatix-test",
                        "type": "tool_call",
                    }
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=response)])


def test_register_sale_tool_writes_structured_arguments(tmp_path) -> None:
    repository = ExcelSalesRepository(tmp_path / "tool.xlsx")
    register_sale, execution = build_register_sale_tool(repository)

    result = register_sale.invoke(
        {
            "customer_name": "Juan Perez",
            "product": "laptop",
            "quantity": 5,
            "amount": "2500",
            "price_basis": "total",
            "currency": "USD",
        }
    )

    assert result["status"] == "inserted"
    assert execution.inserted is True
    assert execution.sale is not None
    assert execution.sale.unit_price == Decimal("500.00")
    assert len(repository.list_all()) == 1


def test_langgraph_agent_executes_tool_and_confirms_without_cloud_call(tmp_path) -> None:
    repository = ExcelSalesRepository(tmp_path / "agent.xlsx")

    outcome = SalesAgent(ToolCallingFakeModel(), repository).process(
        "Agrega una venta de 5 laptops por $2500 para Juan Perez"
    )

    assert outcome.inserted is True
    assert outcome.sale is not None
    assert outcome.sale.total_amount == Decimal("2500.00")
    assert outcome.message == "Venta registrada correctamente."
    assert len(repository.list_all()) == 1
