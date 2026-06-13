"""Pool de conexões SQLite assíncronas."""

from backend.storage.sqlite.pool import AsyncConnectionPool

__all__ = ["AsyncConnectionPool"]
