"""NATS embutido como sidecar do backend — persistência de fila/KV sem Redis.

Mesmo padrão de spawn que o Electron já usa pro backend Python
(``electron/src/main.ts``: resolve o binário, escolhe porta livre, lê stdout
pra achar o sinal de "pronto", encerra limpo no shutdown) — aqui é o backend
Python que sobe o ``nats-server`` como SEU PRÓPRIO sidecar, um nível abaixo,
disponível igualmente em desktop e em modo servidor/VPS.

O binário ``nats-server`` (Go, ~15-20MB, sem dependências) é embutido no
build de distribuição do mesmo jeito que ``frontend/dist`` — baixado uma vez
no CI e colocado ao lado do binário Nuitka. Em dev, ``shutil.which`` resolve
uma instalação local (ex.: ``choco install nats-server`` / ``brew install
nats-server``); sem o binário disponível, o sidecar não sobe e
``get_mq()``/``get_kv()`` caem pro fallback em memória — nunca impede o
backend de iniciar.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
import socket
from pathlib import Path

logger = logging.getLogger(__name__)

_proc: asyncio.subprocess.Process | None = None
_url: str | None = None

_READY_TIMEOUT_S = 10.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _resolve_binary() -> str | None:
    """Localiza o binário ``nats-server`` — PATH (dev) ou resource embutido (build)."""
    from_path = shutil.which("nats-server")
    if from_path:
        return from_path

    # Build de distribuição: binário embutido ao lado do executável Nuitka,
    # mesmo mecanismo de resource extra do frontend/dist.
    bundled = (
        Path(__file__).resolve().parent.parent.parent / "resources" / "nats-server"
    )
    for candidate in (bundled, bundled.with_suffix(".exe")):
        if candidate.is_file():
            return str(candidate)
    return None


async def ensure_nats_sidecar() -> str | None:
    """Sobe (ou reusa) o sidecar ``nats-server`` com JetStream habilitado.

    Retorna a URL de conexão (``nats://127.0.0.1:<porta>``) ou ``None`` se o
    binário não estiver disponível ou o processo falhar ao iniciar — nesse
    caso o chamador (``get_mq``/``get_kv``) deve degradar pro fallback de
    memória, nunca impedir o backend de subir.
    """
    global _proc, _url

    if _proc is not None and _proc.returncode is None:
        return _url

    binary = _resolve_binary()
    if binary is None:
        logger.info(
            "nats_sidecar: binário nats-server não encontrado — sem persistência de fila"
        )
        return None

    store_dir = Path.home() / ".vectora" / "nats"
    store_dir.mkdir(parents=True, exist_ok=True)
    port = _free_port()

    try:
        proc = await asyncio.create_subprocess_exec(
            binary,
            "-js",
            "-sd",
            str(store_dir),
            "-p",
            str(port),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception:
        logger.warning("nats_sidecar: falha ao spawnar nats-server", exc_info=True)
        return None

    ready = await _wait_ready(proc)
    if not ready:
        with_kill(proc)
        return None

    _proc = proc
    _url = f"nats://127.0.0.1:{port}"
    logger.info("nats_sidecar: pronto em %s (store=%s)", _url, store_dir)
    return _url


async def _wait_ready(proc: asyncio.subprocess.Process) -> bool:
    """Lê o stdout até ver a linha de "Server is ready" ou o processo morrer."""
    if proc.stdout is None:
        return False
    try:
        async with asyncio.timeout(_READY_TIMEOUT_S):
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    return False
                line = raw.decode("utf-8", errors="replace")
                if "Server is ready" in line:
                    return True
    except TimeoutError:
        logger.warning("nats_sidecar: timeout esperando o servidor ficar pronto")
        return False


def with_kill(proc: asyncio.subprocess.Process) -> None:
    """Mata um processo que falhou o handshake de prontidão — best-effort."""
    with contextlib.suppress(Exception):
        proc.kill()


async def stop_nats_sidecar() -> None:
    """Encerra o sidecar, se estiver rodando. Idempotente."""
    global _proc, _url

    if _proc is None:
        return
    proc = _proc
    _proc = None
    _url = None
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except TimeoutError:
        proc.kill()
    except Exception:
        logger.warning("nats_sidecar: erro ao encerrar", exc_info=True)


def current_url() -> str | None:
    """URL do sidecar já ativo, sem tentar subir um novo — usado por get_mq/get_kv."""
    return _url if _proc is not None and _proc.returncode is None else None
