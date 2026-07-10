"""Derivação e unicidade de username — a identidade do app é por username,
não por email (o email pertence ao company/services, não ao app local).
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from collections.abc import Callable


def slugify_username(name: str) -> str:
    """Deriva um username-base do nome: minúsculas, sem acento, só ``[a-z0-9]``.

    Ex.: ``"Bruno Soares"`` → ``"brunosoares"``; ``"José"`` → ``"jose"``.
    Nome vazio (ou sem caractere aproveitável) cai em ``"user"``.
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]", "", ascii_only.lower())
    return slug or "user"


def unique_username(base: str, is_taken: Callable[[str], bool]) -> str:
    """Garante um username livre a partir de ``base``.

    Se o slug de ``base`` está livre, devolve-o; senão gera ``base#NNNN`` com 4
    dígitos aleatórios (só números) até achar um livre — o formato de colisão
    pedido (ex.: ``bruno#4821``).
    """
    slug = slugify_username(base)
    if not is_taken(slug):
        return slug
    while True:
        candidate = f"{slug}#{secrets.randbelow(10000):04d}"
        if not is_taken(candidate):
            return candidate
