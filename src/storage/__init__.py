"""Camada de storage do Vectora.

Módulos:
    sqlite/   — pool de conexões aiosqlite com PRAGMAs de hardening
    lancedb/  — cache de conexões + índices IVF/FTS
    (F2) migrations/  — runner de schema versioning
    (F3) protocols.py — Protocols tipados para todos os backends
    (F3) factory.py   — singletons de checkpointer, store, vector_store
"""
