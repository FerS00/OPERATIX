"""Inbound/outbound channel adapters for OPERATIX."""

from backend.app.channels.telegram import TelegramChannel, TelegramUpdate

__all__ = ["TelegramChannel", "TelegramUpdate"]
