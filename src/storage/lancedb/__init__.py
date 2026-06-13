"""Helpers de conexão e índice para LanceDB (lite mode)."""

from src.storage.lancedb.connection import LanceDBConnectionCache, get_lancedb
from src.storage.lancedb.index import create_ivf_index
from src.storage.lancedb.optimize import optimize_table, schedule_optimize

__all__ = [
    "LanceDBConnectionCache",
    "create_ivf_index",
    "get_lancedb",
    "optimize_table",
    "schedule_optimize",
]
