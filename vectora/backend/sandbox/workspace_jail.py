"""Worker jailado persistente por workspace — ponto de integração único do
AI Jail para as tools que tocam filesystem/shell (`terminal`, `file_write`,
`edit_file`, PTY interativo).

Nasce sob demanda na 1ª ação sandboxável de uma workspace com `[sandbox]`
habilitado e fica vivo enquanto a workspace tiver sessão ativa — nunca um
``bwrap`` novo por chamada. Reflete o mesmo princípio do ``ai-jail``
original (uma sessão de trabalho, um processo jailado), adaptado à
arquitetura de processo único e multi-workspace do Vectora.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from backend.sandbox.dry_run import build_bwrap_command
from backend.sandbox.policy import SandboxPolicy

logger = logging.getLogger(__name__)

DEFAULT_IDLE_TIMEOUT_S = 600.0


class WorkerSpawnError(RuntimeError):
    """bwrap ausente/sem permissão — nunca cai silenciosamente pra execução
    sem sandbox."""


@dataclass
class JailedWorker:
    workspace_id: str
    proc: asyncio.subprocess.Process
    last_used: float = field(default_factory=time.monotonic)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _next_id: int = field(default=0, init=False)

    async def request(self, op: str, **kwargs: Any) -> dict[str, Any]:
        async with self._lock:
            self.last_used = time.monotonic()
            self._next_id += 1
            req_id = self._next_id
            payload = {"op": op, "id": req_id, **kwargs}
            if self.proc.stdin is None or self.proc.stdout is None:
                raise RuntimeError("worker jailado sem stdin/stdout conectados")
            self.proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
            await self.proc.stdin.drain()
            line = await self.proc.stdout.readline()
            if not line:
                raise RuntimeError("worker jailado encerrou inesperadamente")
            return json.loads(line)

    def is_alive(self) -> bool:
        return self.proc.returncode is None

    async def close(self) -> None:
        if self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=5.0)
            except TimeoutError:
                self.proc.kill()
                await self.proc.wait()


class WorkspaceJailManager:
    """Singleton do processo backend — um worker por ``workspace_id``."""

    def __init__(self, idle_timeout_s: float = DEFAULT_IDLE_TIMEOUT_S) -> None:
        self._workers: dict[str, JailedWorker] = {}
        self._spawn_lock = asyncio.Lock()
        self._idle_timeout_s = idle_timeout_s

    async def get_or_spawn(
        self, workspace_id: str, workspace_dir: str, policy: SandboxPolicy
    ) -> JailedWorker:
        if not policy.enabled:
            raise WorkerSpawnError("sandbox não habilitado para esta workspace")
        async with self._spawn_lock:
            existing = self._workers.get(workspace_id)
            if existing is not None and existing.is_alive():
                return existing
            worker = await self._spawn(workspace_id, workspace_dir, policy)
            self._workers[workspace_id] = worker
            return worker

    async def _spawn(
        self, workspace_id: str, workspace_dir: str, policy: SandboxPolicy
    ) -> JailedWorker:
        argv = build_bwrap_command(
            policy, workspace_dir, [sys.executable, "-m", "backend.sandbox.worker"]
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            logger.warning("sandbox: binário bwrap não encontrado no sistema")
            raise WorkerSpawnError(
                "bwrap não está instalado neste sistema — sandbox indisponível."
            ) from exc
        except PermissionError as exc:
            logger.warning("sandbox: sem permissão para executar o binário bwrap")
            raise WorkerSpawnError(
                "sem permissão para executar bwrap — sandbox indisponível."
            ) from exc
        return JailedWorker(workspace_id=workspace_id, proc=proc)

    async def close(self, workspace_id: str) -> None:
        worker = self._workers.pop(workspace_id, None)
        if worker is not None:
            await worker.close()

    async def close_idle(self) -> None:
        now = time.monotonic()
        stale = [
            wid
            for wid, w in self._workers.items()
            if now - w.last_used > self._idle_timeout_s
        ]
        for wid in stale:
            await self.close(wid)


jail_manager = WorkspaceJailManager()
