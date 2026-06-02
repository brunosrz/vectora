"""Spawn do servidor Next.js como sidecar do binário compilado.

Quando o Vectora roda como binário Nuitka (produto comercial), o chat web é
embutido na forma do build standalone do Next.js (``chat/.next/standalone``).
Este módulo:

1. Localiza o standalone embutido (Nuitka onefile extrai para uma pasta
   temporária; usamos ``__compiled__`` para detectar).
2. Reserva uma porta TCP efêmera no loopback.
3. Spawna ``node server.js`` apontando para essa porta.
4. Espera o sidecar responder em ``http://127.0.0.1:<porta>/``.
5. Exporta ``VECTORA_FRONTEND_URL`` para o FastAPI fazer o proxy reverso.
6. Garante encerramento limpo via ``atexit``.

Em dev (sem Nuitka), o standalone não existe — o usuário roda ``pnpm dev``
manualmente (porta 3000) e o backend já aponta para lá por padrão.
"""

from __future__ import annotations

import atexit
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_sidecar: subprocess.Popen | None = None


def _find_standalone_root() -> Path | None:
    """Localiza ``chat_standalone/`` extraído pelo Nuitka.

    Em onefile, o Nuitka extrai os data dirs para uma pasta temporária e
    expõe via ``__compiled__.containing_dir``. Em standalone, fica ao lado
    do .exe. Em dev (não compilado), retorna ``None``.
    """
    candidates: list[Path] = []

    compiled = getattr(sys, "__compiled__", None)
    if compiled is not None and hasattr(compiled, "containing_dir"):
        candidates.append(Path(compiled.containing_dir) / "chat_standalone")

    # Nuitka onefile expõe o diretório de extração via env var.
    bootstrap_dir = os.environ.get("NUITKA_ONEFILE_PARENT")
    if bootstrap_dir:
        candidates.append(Path(bootstrap_dir) / "chat_standalone")

    # Fallback: ao lado do executável atual.
    candidates.append(Path(sys.executable).resolve().parent / "chat_standalone")

    for c in candidates:
        if (c / "server.js").is_file():
            return c
    return None


def _reserve_port() -> int:
    """Pega uma porta TCP livre no loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_ready(port: int, timeout_s: float = 30.0) -> bool:
    """Polling TCP até a porta aceitar conexões ou timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def start_next_sidecar() -> str | None:
    """Inicia o Next.js standalone se houver bundle disponível.

    Retorna a URL onde o sidecar está rodando (e exporta em
    ``VECTORA_FRONTEND_URL``), ou ``None`` se não houver bundle embutido
    (modo dev — usuário roda pnpm dev manualmente).
    """
    global _sidecar
    if _sidecar is not None:
        return os.environ.get("VECTORA_FRONTEND_URL")

    root = _find_standalone_root()
    if root is None:
        logger.debug("next_sidecar: bundle não encontrado — assumindo dev mode")
        return None

    node = shutil.which("node")
    if node is None:
        logger.error("next_sidecar: Node.js não está no PATH — chat web indisponível")
        return None

    port = _reserve_port()
    server_js = root / "server.js"

    env = {
        **os.environ,
        "PORT": str(port),
        "HOSTNAME": "127.0.0.1",
        "NODE_ENV": "production",
    }

    logger.info("next_sidecar: subindo Next.js em http://127.0.0.1:%d", port)
    _sidecar = subprocess.Popen(  # nosec B603 — args controlados
        [node, str(server_js)],
        cwd=str(root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    atexit.register(stop_next_sidecar)

    if not _wait_ready(port):
        logger.error("next_sidecar: Next.js não respondeu em 30s")
        stop_next_sidecar()
        return None

    url = f"http://127.0.0.1:{port}"
    os.environ["VECTORA_FRONTEND_URL"] = url
    logger.info("next_sidecar: pronto em %s", url)
    return url


def stop_next_sidecar() -> None:
    """Encerra o sidecar do Next.js."""
    global _sidecar
    if _sidecar is None:
        return
    try:
        _sidecar.terminate()
        try:
            _sidecar.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _sidecar.kill()
    except Exception:
        pass
    finally:
        _sidecar = None
