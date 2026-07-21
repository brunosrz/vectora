"""Electron como sidecar do backend — spawnado de dentro do lifespan do
FastAPI (mesmo padrão async de ``backend/scheduling/nats_sidecar.py``), não
do bootstrap síncrono da CLI (``backend/main.py::_run_start``).

Isso mantém `vectora start` leve pra quem só quer a API REST (VPS/Docker/
CI, ou qualquer client batendo direto no backend): o processo ASGI decide
sozinho, no seu próprio startup, se faz sentido subir uma janela — o
Electron nasce (ou não) como qualquer outro sidecar opcional (NATS,
embedding worker, etc.), não como parte do bootstrap da CLI.

A decisão de *tentar* (``should_spawn_electron``) ainda precisa acontecer
cedo, em ``_run_start``, porque ela também decide o transporte IPC (unix
socket/named pipe) antes do uvicorn subir — mas o *spawn* em si só roda
aqui, dentro do event loop já rodando do FastAPI.
"""

from __future__ import annotations

import asyncio
import logging
import os

from backend.services.electron_launcher import resolve_electron_launch
from backend.services.subprocess_logging import pipe_to_logger
from backend.services.tray import has_display

logger = logging.getLogger(__name__)

_proc: asyncio.subprocess.Process | None = None
_log_task: asyncio.Task | None = None
_spawn_lock: asyncio.Lock | None = None


def _get_spawn_lock() -> asyncio.Lock:
    global _spawn_lock
    if _spawn_lock is None:
        _spawn_lock = asyncio.Lock()
    return _spawn_lock


def should_spawn_electron() -> bool:
    """True quando este processo deve se autoeleger e subir o Electron:
    não já rodando sob Electron (``VECTORA_DESKTOP`` setado externamente),
    sem ``--headless``, com display disponível, e o build de dev do
    Electron resolvível (``scons frontend``/``pnpm --dir frontend run
    electron:build`` já rodou). Chamada por ``_run_start`` (decide transporte IPC cedo) e
    reaproveitada aqui só como referência — a decisão real de spawnar
    chega via env (``VECTORA_SPAWN_ELECTRON``), setado por quem chamou
    esta função primeiro.
    """
    if os.environ.get("VECTORA_DESKTOP"):
        return False
    if os.environ.get("VECTORA_HEADLESS"):
        return False
    if not has_display():
        return False
    return resolve_electron_launch() is not None


async def ensure_electron_sidecar() -> asyncio.subprocess.Process | None:
    """Sobe o Electron (dev) como sidecar, se ainda não estiver rodando.

    Idempotente — chamadas concorrentes reusam o mesmo processo (mesmo
    padrão de ``_spawn_lock`` de ``nats_sidecar.py``, que evitou dois
    processos subindo em corrida). Lê porta/pipe já decididos por
    ``_run_start`` via ``VECTORA_PORT``/``VECTORA_IPC_PIPE`` no ambiente do
    próprio processo — nunca lança, retorna ``None`` em qualquer falha (o
    backend segue de pé sem janela).
    """
    global _proc, _log_task

    async with _get_spawn_lock():
        if _proc is not None and _proc.returncode is None:
            return _proc

        launch = resolve_electron_launch()
        if launch is None:
            return None
        exe, exe_args = launch

        env = {**os.environ, "VECTORA_EXTERNAL_BACKEND": "1"}
        try:
            proc = await asyncio.create_subprocess_exec(
                exe,
                *exe_args,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except Exception:
            logger.exception("electron_sidecar: falha ao spawnar Electron (dev)")
            return None

        logger.info("electron_sidecar: Electron (dev) spawnado, pid=%d", proc.pid)
        _proc = proc
        _log_task = asyncio.create_task(
            pipe_to_logger(proc.stdout, logger, prefix="electron")
        )
        return proc


async def stop_electron_sidecar() -> None:
    """Encerra o sidecar Electron, se estiver rodando. Idempotente."""
    global _proc, _spawn_lock, _log_task

    _spawn_lock = None  # mesmo motivo do nats_sidecar: solta o lock preso ao loop

    if _log_task is not None:
        _log_task.cancel()
        _log_task = None

    if _proc is None:
        return
    proc = _proc
    _proc = None
    if proc.returncode is not None:
        return
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=10.0)
    except TimeoutError:
        proc.kill()
    except Exception:
        logger.warning("electron_sidecar: erro ao encerrar", exc_info=True)
