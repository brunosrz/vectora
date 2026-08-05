"""Padrões compartilhados entre sidecars de subprocesso (NATS, Electron
dev, ver ``backend/scheduling/nats_sidecar.py`` e ``backend/services/
electron_sidecar.py``) — lock de spawn lazy-init e encerramento gracioso
com timeout. Extraído porque os dois módulos tinham a mesma lógica
palavra-por-palavra.
"""

from __future__ import annotations

import asyncio
import logging


class LazyLock:
    """``asyncio.Lock()`` criado sob demanda, não no import — um lock de
    módulo criado antes de qualquer event loop rodar fica preso ao
    primeiro loop que o tocar; uma segunda chamada com event loop novo
    (comum na suíte pytest-asyncio, um loop por teste) levanta "Lock is
    bound to a different event loop". Lazy-init garante que o lock sempre
    pertence ao loop atual. ``reset()`` solta a referência — usado no
    shutdown do sidecar, entre chamadas de teste."""

    def __init__(self) -> None:
        self._lock: asyncio.Lock | None = None

    def get(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def reset(self) -> None:
        self._lock = None


async def terminate_gracefully(
    proc: asyncio.subprocess.Process,
    *,
    timeout_seconds: float,
    logger: logging.Logger,
    log_prefix: str,
) -> None:
    """``terminate()`` → espera ``timeout_seconds``s → ``kill()`` se não
    morreu a tempo. Nunca lança — best-effort, loga qualquer exceção além
    do timeout esperado.

    ``ProcessLookupError`` é tratado como caso esperado (idempotente), não
    erro: o processo já pode ter saído sozinho entre o momento em que o
    shutdown decide encerrá-lo e a chamada a ``terminate()`` — comum sob
    ``CancelledError`` do lifespan encadeando com o encerramento do
    sidecar. Logar isso como warning com traceback completo só polui o log
    de shutdown sem indicar nenhum problema real.
    """
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=timeout_seconds)
    except TimeoutError:
        proc.kill()
    except ProcessLookupError:
        logger.debug("%s: processo já havia saído antes do terminate()", log_prefix)
    except Exception:
        logger.warning("%s: erro ao encerrar", log_prefix, exc_info=True)
