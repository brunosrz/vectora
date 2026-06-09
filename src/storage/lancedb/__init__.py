"""Helpers de conexão e índice para LanceDB (lite mode)."""

from src.storage.lancedb.connection import LanceDBConnectionCache, get_lancedb
from src.storage.lancedb.index import create_ivf_index
from src.storage.lancedb.optimize import optimize_table, schedule_optimize

__all__ = [
    "LanceDBConnectionCache",
    "get_lancedb",
    "create_ivf_index",
    "optimize_table",
    "schedule_optimize",
]
