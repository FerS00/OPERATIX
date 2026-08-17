"""Small Telegram Bot API adapter using free long polling.

The adapter is deliberately independent from FastAPI and the domain. It does not
interpret commands or access SQLAlchemy; callers provide a handler for each update.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import Any

import httpx


class TelegramError(RuntimeError):
    """Raised when the Telegram Bot API cannot be reached or rejects a request."""


class TelegramConfigurationError(TelegramError):
    """Raised when polling is attempted without a bot token."""


@dataclass(frozen=True, slots=True)
class TelegramUpdate:
    """Minimal channel message passed to the application layer."""

    update_id: int
    chat_id: str
    text: str
    username: str | None = None


class TelegramChannel:
    """Telegram transport with no Telegram-specific SDK dependency."""

    def __init__(
        self,
        token: str,
        *,
        request_timeout_seconds: int = 35,
        poll_interval_seconds: int = 5,
    ) -> None:
        self.token = token.strip()
        self.request_timeout_seconds = request_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    @property
    def enabled(self) -> bool:
        """Return whether a token has been configured without exposing it."""
        return bool(self.token)

    def get_updates(self, *, offset: int | None = None, timeout: int = 25) -> list[TelegramUpdate]:
        """Fetch text messages using Telegram long polling."""
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            payload["offset"] = offset
        response = self._request("getUpdates", payload)
        updates: list[TelegramUpdate] = []
        for item in response:
            message = item.get("message") or {}
            chat = message.get("chat") or {}
            text = message.get("text")
            if text is None or "id" not in chat or "update_id" not in item:
                continue
            sender = message.get("from") or {}
            updates.append(
                TelegramUpdate(
                    update_id=int(item["update_id"]),
                    chat_id=str(chat["id"]),
                    text=str(text),
                    username=sender.get("username"),
                )
            )
        return updates

    def send_message(self, chat_id: str, text: str) -> dict[str, Any]:
        """Send one text response and return Telegram's result payload."""
        if not text.strip():
            raise ValueError("El mensaje no puede estar vacío")
        result = self._request("sendMessage", {"chat_id": chat_id, "text": text})
        return result[0] if result else {}

    def poll(
        self,
        handler: Callable[[TelegramUpdate], None],
        *,
        stop_event: Event | None = None,
        initial_offset: int | None = None,
    ) -> None:
        """Run local long polling until ``stop_event`` is set."""
        if not self.enabled:
            raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN no está configurado")
        event = stop_event or Event()
        offset = initial_offset
        while not event.is_set():
            try:
                updates = self.get_updates(offset=offset)
                for update in updates:
                    handler(update)
                    offset = update.update_id + 1
            except TelegramError:
                if event.wait(self.poll_interval_seconds):
                    break

    def _request(self, method: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.enabled:
            raise TelegramConfigurationError("TELEGRAM_BOT_TOKEN no está configurado")
        try:
            with httpx.Client(
                base_url="https://api.telegram.org",
                timeout=self.request_timeout_seconds,
            ) as client:
                response = client.post(f"/bot{self.token}/{method}", data=payload)
                response.raise_for_status()
                decoded = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as error:
            raise TelegramError("No se pudo contactar con Telegram") from error
        if not decoded.get("ok"):
            raise TelegramError("Telegram rechazó la solicitud")
        result = decoded.get("result", [])
        return result if isinstance(result, list) else [result]
