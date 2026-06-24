"""Grafo de conhecimento nativo do Vectora — base copiada do graphify (MIT).

Fonte original: https://github.com/safishamsi/graphify (Safi Shamsi, MIT).
Estes módulos são o pipeline puro do graphify (AST via tree-sitter, build NetworkX,
clustering Leiden, analyze, report, export) copiados para serem **nativizados**:
refatorados incrementalmente para a arquitetura do Vectora (async, LLM próprio,
storage por workspace). Enquanto a refatoração não termina, o pacote fica excluído
dos gates estritos (ruff/ty/bandit) — ver pyproject e .pre-commit-config.

A extração semântica (pass 3) NÃO usa o `llm.py` do graphify: passa pelo LLM ativo
do Vectora (`backend.services.utils.load_llm`) em `semantic.py`.
"""
