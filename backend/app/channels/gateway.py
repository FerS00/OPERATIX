"""Safe Telegram command gateway with confirmation and per-chat rate limits."""

from __future__ import annotations

import shlex
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.channels.telegram import TelegramChannel, TelegramUpdate
from backend.app.models.security import User
from backend.app.orchestrator import AIOrchestrator


class TelegramCommandError(ValueError):
    """Raised when a Telegram command is invalid or cannot be authorized."""


@dataclass(frozen=True, slots=True)
class SaleRequest:
    """Structured sale payload collected from a Telegram command."""

    customer_id: str
    product_id: str
    quantity: int
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class PendingConfirmation:
    """Action awaiting an explicit confirmation from the same chat."""

    confirmation_id: str
    chat_id: str
    request: SaleRequest
    expires_at: datetime


SaleExecutor = Callable[[str, SaleRequest], str]


class ChatRateLimiter:
    """Small in-memory fixed-window limiter suitable for one local process."""

    def __init__(self, *, max_requests: int = 10, window_seconds: int = 60) -> None:
        if max_requests < 1 or window_seconds < 1:
            raise ValueError("El límite y la ventana deben ser positivos")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, chat_id: str) -> bool:
        now = time.monotonic()
        history = self._requests[chat_id]
        cutoff = now - self.window_seconds
        while history and history[0] <= cutoff:
            history.popleft()
        if len(history) >= self.max_requests:
            return False
        history.append(now)
        return True


class TelegramCommandGateway:
    """Translate only explicit structured commands into confirmed sale callbacks."""

    def __init__(
        self,
        channel: TelegramChannel,
        sale_executor: SaleExecutor,
        *,
        confirmation_ttl_seconds: int = 120,
        max_requests_per_minute: int = 10,
    ) -> None:
        if confirmation_ttl_seconds < 1:
            raise ValueError("La confirmación debe tener una duración positiva")
        self.channel = channel
        self.sale_executor = sale_executor
        self.confirmation_ttl = timedelta(seconds=confirmation_ttl_seconds)
        self.rate_limiter = ChatRateLimiter(max_requests=max_requests_per_minute)
        self._pending: dict[tuple[str, str], PendingConfirmation] = {}

    def handle_update(self, update: TelegramUpdate) -> str:
        """Process one message and send exactly one bounded text response."""
        if not self.rate_limiter.allow(update.chat_id):
            return self._reply(
                update.chat_id, "Demasiadas solicitudes. Intenta de nuevo en un minuto."
            )

        try:
            words = shlex.split(update.text)
        except ValueError:
            return self._reply(update.chat_id, "No pude leer el comando. Usa /ayuda.")
        if not words:
            return self._reply(update.chat_id, "Usa /ayuda para ver los comandos disponibles.")

        command = words[0].lower()
        if command in {"/ayuda", "/help"}:
            return self._reply(update.chat_id, self.help_text())
        if command in {"/venta", "/sale"}:
            return self._request_sale(update.chat_id, words[1:])
        if command in {"/confirmar", "/confirm"}:
            return self._confirm(update.chat_id, words[1:])
        if command in {"/cancelar", "/cancel"}:
            return self._cancel(update.chat_id, words[1:])
        return self._reply(update.chat_id, "Comando no reconocido. Usa /ayuda.")

    @staticmethod
    def help_text() -> str:
        return (
            "Comandos disponibles:\n"
            "/venta <cliente_id> <producto_id> <cantidad> [idempotency_key]\n"
            "/confirmar <código>\n"
            "/cancelar <código>\n"
            "Una venta siempre requiere confirmación explícita."
        )

    def _request_sale(self, chat_id: str, arguments: list[str]) -> str:
        if len(arguments) not in {3, 4}:
            return self._reply(
                chat_id, "Formato: /venta <cliente_id> <producto_id> <cantidad> [clave]"
            )
        customer_id, product_id, raw_quantity = arguments[:3]
        try:
            quantity = int(raw_quantity)
        except ValueError:
            return self._reply(chat_id, "La cantidad debe ser un entero positivo.")
        if quantity <= 0:
            return self._reply(chat_id, "La cantidad debe ser un entero positivo.")
        idempotency_key = arguments[3] if len(arguments) == 4 else f"telegram-{uuid4().hex}"
        request = SaleRequest(customer_id, product_id, quantity, idempotency_key)
        confirmation_id = uuid4().hex[:10]
        pending = PendingConfirmation(
            confirmation_id=confirmation_id,
            chat_id=chat_id,
            request=request,
            expires_at=datetime.now(UTC) + self.confirmation_ttl,
        )
        self._pending[(chat_id, confirmation_id)] = pending
        return self._reply(
            chat_id,
            f"Confirma la venta de {quantity} unidad(es) del producto {product_id} "
            f"para {customer_id}: /confirmar {confirmation_id}",
        )

    def _confirm(self, chat_id: str, arguments: list[str]) -> str:
        if len(arguments) != 1:
            return self._reply(chat_id, "Formato: /confirmar <código>")
        key = (chat_id, arguments[0])
        pending = self._pending.pop(key, None)
        if pending is None:
            return self._reply(chat_id, "La confirmación no existe o ya fue utilizada.")
        if pending.expires_at < datetime.now(UTC):
            return self._reply(chat_id, "La confirmación expiró; crea una nueva venta.")
        try:
            result = self.sale_executor(chat_id, pending.request)
        except Exception:
            return self._reply(
                chat_id, "No se pudo ejecutar la venta. Revisa los datos y permisos."
            )
        return self._reply(chat_id, result)

    def _cancel(self, chat_id: str, arguments: list[str]) -> str:
        if len(arguments) != 1:
            return self._reply(chat_id, "Formato: /cancelar <código>")
        removed = self._pending.pop((chat_id, arguments[0]), None)
        message = "Venta cancelada." if removed else "La confirmación no existe o ya fue utilizada."
        return self._reply(chat_id, message)

    def _reply(self, chat_id: str, message: str) -> str:
        self.channel.send_message(chat_id, message)
        return message


def build_orchestrated_sale_executor(
    session_factory: Callable[[], Session],
    user_resolver: Callable[[Session, str], User | None],
) -> SaleExecutor:
    """Build a callback that invokes only the registered ``create_sale`` tool."""

    def execute(chat_id: str, request: SaleRequest) -> str:
        with session_factory() as session:
            user = user_resolver(session, chat_id)
            if user is None:
                raise TelegramCommandError("Chat de Telegram no vinculado a un usuario")
            result = AIOrchestrator().execute(
                session,
                user,
                "create_sale",
                {
                    "customer_id": request.customer_id,
                    "product_id": request.product_id,
                    "quantity": request.quantity,
                    "idempotency_key": request.idempotency_key,
                },
            )
            sale = result["sale"]
            replayed = " (repetida)" if result["replayed"] else ""
            return f"Venta registrada: {sale.id}{replayed}."

    return execute
