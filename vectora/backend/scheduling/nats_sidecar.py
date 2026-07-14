"""NATS embutido como sidecar do backend — persistência de fila/KV sem Redis.

Mesmo padrão de spawn que o Electron já usa pro backend Python
(``electron/src/main.ts``: resolve o binário, escolhe porta livre, lê stdout
pra achar o sinal de "pronto", encerra limpo no shutdown) — aqui é o backend
Python que sobe o ``nats-server`` como SEU PRÓPRIO sidecar, um nível abaixo,
disponível igualmente em desktop e em modo servidor/VPS.

O binário ``nats-server`` (Go, ~15-20MB, sem dependências) é baixado por
``scons nats`` pra ``vectora/resources/`` e embutido no executável final por
DOIS empacotadores diferentes, então precisa de DOIS caminhos de resolução em
runtime — mesma resolução de bundle congelado que ``server.py::
_chat_static_root`` já usa pro ``frontend/dist``:

- Electron (``electron-builder`` ``extraResources``): resource fica ao lado
  do app empacotado; o processo Electron passa o caminho explícito via
  ``VECTORA_NATS_BINARY``.
- Standalone/VPS (``build-hybrid.py``: Nuitka compila o backend, PyInstaller
  empacota em ``--onedir``): o binário entra via ``--add-binary`` numa pasta
  ``nats/`` dentro do bundle, achado em runtime por ``sys._MEIPASS`` (onedir/
  onefile do PyInstaller) ou ``sys.__compiled__.containing_dir``/
  ``NUITKA_ONEFILE_PARENT`` (onefile do Nuitka puro, sem PyInstaller).

Em dev, ``shutil.which`` resolve uma instalação local (ex.: ``choco install
nats-server`` / ``brew install nats-server``) ou o resource baixado em
``vectora/resources/`` por ``scons nats``. Sem o binário disponível em
NENHUM desses caminhos, o sidecar não sobe e ``get_mq()``/``get_kv()`` caem
pro fallback em memória — nunca impede o backend de iniciar.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import socket
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_proc: asyncio.subprocess.Process | None = None
_url: str | None = None
# Criado sob demanda (não no import) — um asyncio.Lock() de módulo, criado
# antes de qualquer event loop rodar, fica "preso" ao primeiro loop que o
# tocar; um segundo teste/processo com event loop novo (comum na suíte
# pytest-asyncio, um loop por teste) levanta "Lock is bound to a different
# event loop". Lazy-init garante que o lock sempre pertence ao loop atual.
_spawn_lock: asyncio.Lock | None = None

_READY_TIMEOUT_S = 10.0


def _get_spawn_lock() -> asyncio.Lock:
    global _spawn_lock
    if _spawn_lock is None:
        _spawn_lock = asyncio.Lock()
    return _spawn_lock


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _exe_name() -> str:
    return "nats-server.exe" if sys.platform == "win32" else "nats-server"


def _frozen_bundle_bases() -> list[Path]:
    """Diretórios-raiz de bundle congelado onde ``build-hybrid.py`` pode ter
    colocado a pasta ``nats/`` — mesma fonte que ``_chat_static_root`` usa."""
    bases: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bases.append(Path(meipass))
    compiled = getattr(sys, "__compiled__", None)
    if compiled is not None and hasattr(compiled, "containing_dir"):
        bases.append(Path(compiled.containing_dir))
    nuitka_parent = os.environ.get("NUITKA_ONEFILE_PARENT")
    if nuitka_parent:
        bases.append(Path(nuitka_parent))
    return bases


def _resolve_binary() -> str | None:
    """Localiza o binário ``nats-server``.

    Ordem: override explícito (``VECTORA_NATS_BINARY``, apontado pelo Electron
    pro binário empacotado via ``extraResources``) → bundle congelado
    (PyInstaller/Nuitka onefile, pasta ``nats/`` embutida por
    ``build-hybrid.py`` — vence o PATH pra nunca rodar uma versão desalinhada
    instalada à parte na máquina) → PATH (dev, ex.: ``choco/brew install
    nats-server``) → árvore-fonte (``vectora/resources/``, baixado por
    ``scons nats``).
    """
    override = os.getenv("VECTORA_NATS_BINARY")
    if override and Path(override).is_file():
        return override

    exe_name = _exe_name()

    for base in _frozen_bundle_bases():
        candidate = base / "nats" / exe_name
        if candidate.is_file():
            return str(candidate)

    from_path = shutil.which("nats-server")
    if from_path:
        return from_path

    bundled = Path(__file__).resolve().parent.parent.parent / "resources" / exe_name
    if bundled.is_file():
        return str(bundled)
    return None


async def ensure_nats_sidecar() -> str | None:
    """Sobe (ou reusa) o sidecar ``nats-server`` com JetStream habilitado.

    Retorna a URL de conexão (``nats://127.0.0.1:<porta>``) ou ``None`` se o
    binário não estiver disponível ou o processo falhar ao iniciar — nesse
    caso o chamador (``get_mq``/``get_kv``) deve degradar pro fallback de
    memória, nunca impedir o backend de subir.

    ``_spawn_lock`` serializa chamadas concorrentes — sem ele, duas corridas
    passariam pelo check ``_proc is None`` antes de qualquer uma setar
    ``_proc``, subindo dois ``nats-server`` em portas diferentes.
    """
    global _proc, _url

    async with _get_spawn_lock():
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
    global _proc, _url, _spawn_lock

    # Solta a referência ao lock também quando não há processo rodando —
    # entre testes (cada um com seu próprio event loop via pytest-asyncio),
    # sem isso o lock ficaria preso ao loop do teste anterior e o próximo
    # `_get_spawn_lock()` levantaria "Lock is bound to a different event loop".
    _spawn_lock = None

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
