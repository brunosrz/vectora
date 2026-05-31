"""Rastreador de uso por usuário — janela deslizante em memória (R5).

Conta requests por ``user_id`` dentro de uma janela de tempo e expõe o consumo
para o medidor de uso do plano (GET /auth/usage). É single-process: o estado
vive na memória do servidor e zera ao reiniciar — suficiente para o feedback de
uso no chat. Multi-server exigiria um backend compartilhado (Redis), fora deste
escopo.
"""

from __future__ import annotations

import time

__all__ = ["UsageTracker", "usage_tracker"]


class UsageTracker:
    """Conta eventos por usuário numa janela deslizante de ``window_seconds``."""

    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._events: dict[str, list[float]] = {}

    def _prune(self, bucket: list[float], now: float) -> None:
        cutoff = now - self._window
        idx = 0
        for ts in bucket:
            if ts >= cutoff:
                break
            idx += 1
        if idx:
            del bucket[:idx]

    def record(self, user_id: str, *, now: float | None = None) -> None:
        """Registra um request do usuário no instante ``now`` (default: agora)."""
        ts = time.time() if now is None else now
        bucket = self._events.setdefault(user_id, [])
        bucket.append(ts)
        self._prune(bucket, ts)

    def usage(
        self, user_id: str, *, now: float | None = None
    ) -> dict[str, float | int]:
        """Retorna o consumo atual do usuário dentro da janela.

        Campos: ``used``, ``limit``, ``remaining``, ``window_seconds`` e
        ``reset_in_seconds`` (tempo até o evento mais antigo sair da janela).
        """
        ts = time.time() if now is None else now
        bucket = self._events.get(user_id, [])
        self._prune(bucket, ts)
        used = len(bucket)
        reset_in = 0.0
        if bucket:
            reset_in = max(0.0, self._window - (ts - bucket[0]))
        return {
            "used": used,
            "limit": self._limit,
            "remaining": max(0, self._limit - used),
            "window_seconds": self._window,
            "reset_in_seconds": round(reset_in, 1),
        }


#: Instância global compartilhada pelo servidor.
usage_tracker = UsageTracker()
