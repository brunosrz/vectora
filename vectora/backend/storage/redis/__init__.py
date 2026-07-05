"""Backends Redis — armazenamento de histórico de chat."""

from __future__ import annotations

from backend.storage.redis.chat_history import get_chat_history

__all__ = ["get_chat_history"]
