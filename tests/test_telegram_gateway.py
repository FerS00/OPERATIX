import re

from backend.app.channels.gateway import TelegramCommandGateway
from backend.app.channels.telegram import TelegramUpdate


class FakeTelegram:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send_message(self, chat_id: str, text: str):
        self.messages.append((chat_id, text))
        return {}


def test_sale_requires_confirmation_and_cannot_be_replayed() -> None:
    channel = FakeTelegram()
    executed: list[tuple[str, object]] = []
    gateway = TelegramCommandGateway(
        channel, lambda chat_id, request: executed.append((chat_id, request)) or "Venta registrada"
    )

    requested = gateway.handle_update(
        TelegramUpdate(1, "chat-1", "/venta customer-1 product-1 2 order-123")
    )
    confirmation_id = re.search(r"/confirmar ([a-z0-9]+)", requested).group(1)
    confirmed = gateway.handle_update(TelegramUpdate(2, "chat-1", f"/confirmar {confirmation_id}"))
    replay = gateway.handle_update(TelegramUpdate(3, "chat-1", f"/confirmar {confirmation_id}"))

    assert "Confirma" in requested
    assert confirmed == "Venta registrada"
    assert "no existe" in replay
    assert len(executed) == 1
    assert executed[0][0] == "chat-1"


def test_confirmation_is_bound_to_chat_and_rate_limit_is_enforced() -> None:
    channel = FakeTelegram()
    gateway = TelegramCommandGateway(
        channel, lambda _chat_id, _request: "ok", max_requests_per_minute=2
    )

    requested = gateway.handle_update(TelegramUpdate(1, "chat-1", "/venta c p 1"))
    confirmation_id = re.search(r"/confirmar ([a-z0-9]+)", requested).group(1)
    wrong_chat = gateway.handle_update(TelegramUpdate(2, "chat-2", f"/confirmar {confirmation_id}"))
    gateway.handle_update(TelegramUpdate(3, "chat-1", "/ayuda"))
    limited = gateway.handle_update(TelegramUpdate(4, "chat-1", "/ayuda"))

    assert "no existe" in wrong_chat
    assert "Demasiadas" in limited
