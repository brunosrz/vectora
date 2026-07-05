"""Persistência de estado: checkpoints, sessões, KV transiente e traces.

``checkpoint.py`` (checkpointer LangGraph + backup/restore de workspace),
``session.py`` (ciclo de vida de sessão de chat), ``kv.py`` (KV genérico
com fallback Redis/SQLite) e ``tracer.py`` (coleta de traces de execução do
grafo para diagnóstico).
"""
