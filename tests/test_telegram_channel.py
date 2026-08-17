from threading import Event

import pytest

from backend.app.channels.telegram import TelegramChannel, TelegramConfigurationError


def test_telegram_channel_normalizes_text_updates_without_network() -> None:
    channel = TelegramChannel("test-token")
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_request(method: str, payload: dict[str, object]):
        calls.append((method, payload))
        if method == "getUpdates":
            return [
                {
                    "update_id": 10,
                    "message": {"chat": {"id": 99}, "text": "/ventas", "from": {"username": "ana"}},
                },
                {"update_id": 11, "message": {"chat": {"id": 99}, "photo": []}},
            ]
        return [{"message_id": 1}]

    channel._request = fake_request  # type: ignore[method-assign]

    updates = channel.get_updates(offset=10)
    sent = channel.send_message("99", "Resumen listo")

    assert channel.enabled is True
    assert updates[0].chat_id == "99"
    assert updates[0].username == "ana"
    assert sent["message_id"] == 1
    assert calls[0][1]["offset"] == 10
    assert calls[1][0] == "sendMessage"


def test_telegram_poll_stops_after_handler_handles_update() -> None:
    channel = TelegramChannel("test-token")
    stop_event = Event()
    handled: list[str] = []

    def fake_updates(*, offset=None, timeout=25):
        return [type("Update", (), {"update_id": 4, "text": "hola"})()]

    channel.get_updates = fake_updates  # type: ignore[method-assign]
    channel.poll(
        lambda update: (handled.append(update.text), stop_event.set()), stop_event=stop_event
    )

    assert handled == ["hola"]


def test_telegram_requires_token_and_non_empty_messages() -> None:
    channel = TelegramChannel("")

    with pytest.raises(TelegramConfigurationError):
        channel.get_updates()
    with pytest.raises(TelegramConfigurationError):
        channel.poll(lambda _update: None)

    configured = TelegramChannel("token")
    with pytest.raises(ValueError):
        configured.send_message("chat", " ")
