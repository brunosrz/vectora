"""Repassa stdout de um subprocess pro logger Python, linha a linha.

Usado por sidecars/subprocessos filhos (preview de workspace, Electron,
NATS) cujo stdout hoje é descartado (`DEVNULL`) ou herdado sem tratamento —
ambos deixam o operador sem nenhuma pista quando o processo falha.
"""

from __future__ import annotations

import logging
from typing import Protocol


class _LineReader(Protocol):
    async def readline(self) -> bytes: ...


async def pipe_to_logger(
    stream: _LineReader | None,
    logger: logging.Logger,
    prefix: str,
    level: int = logging.INFO,
) -> None:
    """Lê `stream` até EOF, logando cada linha como `"{prefix}: {linha}"`.

    `stream=None` (subprocess sem stdout capturado) é um no-op silencioso —
    não é erro, só não há nada pra repassar.
    """
    if stream is None:
        return
    while True:
        raw = await stream.readline()
        if not raw:
            return
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            logger.log(level, "%s: %s", prefix, line)
