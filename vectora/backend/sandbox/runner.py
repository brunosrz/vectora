"""Ponto de integração único do sandbox — tools que hoje spawnam subprocess
direto (`terminal`, git) chamam `run_sandboxed` em vez de
`asyncio.create_subprocess_exec` quando querem respeitar `vectora.toml`.

Sem `vectora.toml`/seção `[sandbox]` no workspace: `run_sandboxed` roda o
comando normalmente (sem wrapper) — comportamento atual preservado, callers
podem chamar isto incondicionalmente sem regressão.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.sandbox.docker import run_docker_sandboxed
from backend.sandbox.linux import SandboxResult, run_local_sandboxed
from backend.sandbox.modal import run_modal_sandboxed
from backend.sandbox.policy import parse_policy
from backend.sandbox.ssh import run_ssh_sandboxed

logger = logging.getLogger(__name__)

_BACKENDS = {
    "local": run_local_sandboxed,
    "docker": run_docker_sandboxed,
    "ssh": run_ssh_sandboxed,
    "modal": run_modal_sandboxed,
}


async def _run_unsandboxed(
    command: list[str], workspace_dir: str, timeout_s: float
) -> SandboxResult:
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=workspace_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_s
        )
        return SandboxResult(
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
            exit_code=proc.returncode or 0,
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return SandboxResult(
            stdout="",
            stderr=f"Error: comando excedeu o timeout de {timeout_s}s.",
            exit_code=124,
            timed_out=True,
        )


async def run_sandboxed(
    command: list[str], workspace_dir: str, *, timeout_s: float = 60.0
) -> SandboxResult:
    """Lê `vectora.toml` do workspace e despacha pro backend certo.

    `backend` desconhecido em `[sandbox]` falha fechado (nega execução,
    `exit_code=126`) — nunca cai silenciosamente pro modo sem sandbox.
    """
    policy = parse_policy(Path(workspace_dir) / "vectora.toml")
    if not policy.enabled:
        return await _run_unsandboxed(command, workspace_dir, timeout_s)

    backend_fn = _BACKENDS.get(policy.backend)
    if backend_fn is None:
        logger.error(
            "sandbox: backend '%s' não suportado — negando execução (fail-closed)",
            policy.backend,
        )
        return SandboxResult(
            stdout="",
            stderr=f"Error: backend de sandbox '{policy.backend}' não suportado.",
            exit_code=126,
        )
    return await backend_fn(command, workspace_dir, policy, timeout_s=timeout_s)
