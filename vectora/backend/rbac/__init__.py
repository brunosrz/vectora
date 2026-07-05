"""Identidade, RBAC e política de acesso — "quem pode o quê".

``auth.py`` (usuários, roles, JWT, hashing), ``permissions.py`` (hierarquia
RBAC + regras de filesystem), ``tool_policy.py`` (allowlist de tools por
usuário), ``subscription.py`` (gate de feature por plano) e
``safe_roots.py`` (raízes de filesystem permitidas por usuário).
"""
