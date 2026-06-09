"""Camada de storage do Vectora.

Módulos:
    sqlite/      — pool de conexões aiosqlite com PRAGMAs de hardening (F1)
    lancedb/     — cache de conexões + índices IVF/FTS (F1)
    migrations/  — runner de schema versioning (F2)
    protocols.py — Protocols tipados para todos os backends (F3)
    factory.py   — singletons de checkpointer, store, vector_store (F3)
"""
