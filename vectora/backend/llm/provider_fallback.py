"""Fallback automático entre providers de LLM ao esgotar quota.

Quando um provider devolve 429/quota, ``try_with_fallback`` percorre a cadeia
configurada (``llm_fallback_order`` em settings.json), pulando o provider atual
e os sem API key. Cada troca é registrada (ContextVar) para o handler de chat
drenar e notificar o frontend, e propagada via callback ``on_switch``.

Defensivo: erros que NÃO são de quota propagam imediatamente (sem fallback).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

_QUOTA_MARKERS = ("429", "resource_exhausted", "quota", "rate limit", "rate_limit")
_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connecttimeout",
    "readtimeout",
    "connection error",
    "connection refused",
)


class QuotaExhaustedError(Exception):
    """Todos os providers da cadeia esgotaram a quota."""

    def __init__(
        self,
        message: str,
        *,
        model_id: str | None = None,
        provider: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.model_id = model_id
        self.provider = provider
        self.retry_after = retry_after


def is_quota_error(exc: BaseException) -> bool:
    """True se a exceção indica quota/rate-limit esgotada."""
    if isinstance(exc, QuotaExhaustedError):
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _QUOTA_MARKERS)


def is_transient_error(exc: BaseException) -> bool:
    """True se a exceção indica falha transiente (timeout, conexão) — vale tentar o próximo provider."""
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def _provider_of(model_id: str) -> str:
    return model_id.split(":", 1)[0]


def _provider_has_key(provider: str) -> bool:
    """True se o provider tem credencial configurada (ollama é sempre local)."""
    if provider == "ollama":
        return True
    from backend.settings import settings

    keymap = {
        "openai": settings.openai_api_key,
        "google-genai": settings.google_api_key,
        "anthropic": settings.anthropic_api_key,
        "cohere": settings.cohere_api_key,
    }
    return bool(keymap.get(provider))


def _fallback_order() -> list[str]:
    """Ordem de fallback configurada pelo usuário (lista de 'provider:model')."""
    from backend.workspace.runtime_settings import runtime_settings

    order = runtime_settings.get("llm_fallback_order", []) or []
    return [str(x) for x in order] if isinstance(order, list) else []


def get_fallback_chain(current_model_id: str) -> list[str]:
    """Cadeia ordenada de modelos a tentar após o atual esgotar.

    Remove o provider atual (mesma quota) e os providers sem API key.
    """
    current_provider = _provider_of(current_model_id)
    chain: list[str] = []
    for mid in _fallback_order():
        prov = _provider_of(mid)
        if prov == current_provider:
            continue
        if not _provider_has_key(prov):
            continue
        chain.append(mid)
    return chain


# ---------------------------------------------------------------------------
# Fila de trocas (drenada pelo handler de chat para notificar o frontend)
# ---------------------------------------------------------------------------

_PENDING_SWITCHES: ContextVar[list[dict[str, str]] | None] = ContextVar(
    "pending_switches", default=None
)


def record_switch(from_model: str, to_model: str) -> None:
    lst = _PENDING_SWITCHES.get()
    if lst is None:
        lst = []
        _PENDING_SWITCHES.set(lst)
    lst.append({"from": from_model, "to": to_model})


def drain_switches() -> list[dict[str, str]]:
    """Devolve as trocas pendentes e limpa a fila."""
    lst = _PENDING_SWITCHES.get()
    _PENDING_SWITCHES.set(None)
    return list(lst) if lst else []


async def try_with_fallback[T](
    fn: Callable[[str], Awaitable[T]],
    model_id: str,
    *,
    on_switch: Callable[[str, str], Any] | None = None,
) -> T:
    """Executa ``fn(model_id)``; em quota error percorre a cadeia de fallback.

    Erros não-quota propagam de imediato. Esgotada a cadeia → QuotaExhaustedError.
    """
    try:
        return await fn(model_id)
    except Exception as exc:
        if not is_quota_error(exc):
            raise
        last_exc: BaseException = exc
        current = model_id

    for next_mid in get_fallback_chain(model_id):
        record_switch(current, next_mid)
        if on_switch is not None:
            try:
                on_switch(current, next_mid)
            except Exception:
                logger.debug("provider_fallback: on_switch falhou", exc_info=True)
        logger.warning(
            "provider_fallback: quota esgotada em %s → tentando %s", current, next_mid
        )
        try:
            return await fn(next_mid)
        except Exception as exc2:
            if not is_quota_error(exc2):
                raise
            last_exc = exc2
            current = next_mid

    raise QuotaExhaustedError(
        f"Todos os providers esgotaram a quota (último: {current}).",
        model_id=current,
        provider=_provider_of(current),
    ) from last_exc
