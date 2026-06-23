"""PtySession — pseudo-terminal cross-platform (Bloco T, T1).

Abstrai ``pywinpty`` (Windows/ConPTY) e ``ptyprocess`` (macOS/Linux) atrás de
uma única classe assíncrona. I/O externo em **bytes** (o que o WebSocket envia
e recebe); a conversão para str (Windows) é feita dentro da classe.

A leitura roda num executor (a API dos backends é síncrona/bloqueante) e
empurra para uma ``asyncio.Queue`` consumida pelo handler WS.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
from typing import Any

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"


def _load_pty_backend() -> Any:
    """Carrega o backend de PTY da plataforma: pywinpty no Windows, ptyprocess fora.

    Import dinâmico via importlib: as libs são mutuamente exclusivas por SO e não
    resolvem estaticamente na outra plataforma — resolver dinamicamente evita o
    type checker falhar em ``winpty`` no Linux (e vice-versa). Retorna None se o
    backend não estiver instalado; o caller degrada com erro tratado.
    """
    import importlib

    module = "winpty" if _IS_WINDOWS else "ptyprocess"
    try:
        return importlib.import_module(module).PtyProcess
    except Exception:  # pragma: no cover — backend de PTY indisponível na plataforma
        return None


_Backend: Any = _load_pty_backend()


def _default_shell() -> list[str]:
    """Comando do shell padrão da plataforma."""
    if _IS_WINDOWS:
        # Prefere pwsh (PowerShell 7) se disponível; senão cmd.exe.
        from shutil import which

        if which("pwsh.exe"):
            return ["pwsh.exe", "-NoLogo"]
        return ["cmd.exe"]
    shell = os.environ.get("SHELL", "/bin/bash")
    return [shell]


class PtySession:
    """Sessão de pseudo-terminal — wrapper async cross-platform.

    Use ``create()`` (não chame o construtor diretamente) para spawn assíncrono
    e arranque do read-loop. ``read()`` devolve bytes ou ``None`` quando o
    processo encerra.
    """

    def __init__(
        self,
        terminal_id: str,
        workspace_id: str,
        thread_id: str,
        proc: Any,
    ) -> None:
        self.terminal_id = terminal_id
        self.workspace_id = workspace_id
        self.thread_id = thread_id
        self._proc = proc
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=4096)
        self._closed = False
        self._read_task: asyncio.Task | None = None

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        terminal_id: str,
        workspace_id: str,
        thread_id: str,
        cwd: str,
        env: dict[str, str] | None = None,
        cols: int = 80,
        rows: int = 24,
        argv: list[str] | None = None,
    ) -> PtySession:
        if _Backend is None:
            raise RuntimeError(
                "Backend de PTY indisponível (instale pywinpty no Windows ou "
                "ptyprocess no Unix)."
            )

        cmd = argv or _default_shell()
        merged_env = {**os.environ, **(env or {})}

        # pywinpty aceita lista ou string; ptyprocess espera argv (lista).
        try:
            proc = _Backend.spawn(
                cmd,
                dimensions=(rows, cols),
                cwd=cwd,
                env=merged_env,
            )
        except Exception as exc:
            logger.exception("pty_session: falha ao spawn %s", cmd)
            raise RuntimeError(f"Falha ao iniciar shell: {exc}") from exc

        session = cls(
            terminal_id=terminal_id,
            workspace_id=workspace_id,
            thread_id=thread_id,
            proc=proc,
        )
        session._read_task = asyncio.create_task(
            session._read_loop(), name=f"pty-read-{terminal_id}"
        )
        logger.info(
            "pty_session: spawn %s (terminal=%s workspace=%s)",
            cmd[0],
            terminal_id,
            workspace_id,
        )
        return session

    # ── Read / Write / Resize / Close ────────────────────────────────────────

    async def _read_loop(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            while not self._closed:
                try:
                    data = await loop.run_in_executor(
                        None, lambda: self._proc.read(4096)
                    )
                except EOFError:
                    break
                except Exception:
                    if self._closed:
                        return
                    logger.debug("pty_session: erro no read-loop %s", self.terminal_id)
                    break

                if not data:
                    break
                if isinstance(data, str):
                    data = data.encode("utf-8", errors="replace")
                try:
                    await self._queue.put(data)
                except asyncio.CancelledError:
                    return
        finally:
            await self._queue.put(None)

    async def read(self) -> bytes | None:
        """Devolve o próximo bloco de saída do PTY, ou None quando encerra."""
        return await self._queue.get()

    def write(self, data: bytes) -> None:
        if self._closed:
            return
        try:
            if _IS_WINDOWS:
                # pywinpty espera str
                self._proc.write(data.decode("utf-8", errors="replace"))
            else:
                self._proc.write(data)
        except Exception:
            logger.debug("pty_session: write falhou %s", self.terminal_id)

    def resize(self, cols: int, rows: int) -> None:
        try:
            self._proc.setwinsize(rows, cols)
        except Exception:
            logger.debug("pty_session: resize falhou %s", self.terminal_id)

    def is_alive(self) -> bool:
        try:
            return bool(self._proc.isalive())
        except Exception:
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._proc.terminate(force=True)
        except Exception:
            logger.debug("pty_session: terminate falhou %s", self.terminal_id)
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        logger.info("pty_session: encerrado %s", self.terminal_id)
