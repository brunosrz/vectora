"""Backend de sandbox via Docker — roda o comando dentro de um container
efêmero (`docker run --rm`). Imagem configurável em `vectora.toml`
(`[sandbox] docker_image`), default uma imagem mínima. `lockdown` nega
rede (`--network none`), mesmo princípio do backend `local` (bwrap).
"""

from __future__ import annotations

import asyncio
import logging

from backend.sandbox.linux import SandboxResult
from backend.sandbox.policy import SandboxPolicy

logger = logging.getLogger(__name__)

DEFAULT_DOCKER_IMAGE = "python:3.13-slim"


def build_docker_command(
    policy: SandboxPolicy, workspace_dir: str, command: list[str]
) -> list[str]:
    """Monta o argv de `docker run` — separado da execução pra ser
    testável sem o binário `docker` instalado (mesmo espírito de
    `dry_run.build_bwrap_command`)."""
    image = policy.docker_image or DEFAULT_DOCKER_IMAGE
    argv = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{workspace_dir}:{workspace_dir}",
        "-w",
        workspace_dir,
    ]
    if policy.lockdown:
        argv += ["--network", "none"]
    argv += [image, *command]
    return argv


async def run_docker_sandboxed(
    command: list[str],
    workspace_dir: str,
    policy: SandboxPolicy,
    *,
    timeout_s: float = 60.0,
) -> SandboxResult:
    """Roda `command` num container Docker efêmero. `docker` ausente do
    sistema devolve `exit_code=127` com mensagem clara; sem permissão de
    execução (`PermissionError`) devolve `exit_code=126` (convenção POSIX)
    — nunca levanta exceção (tools defensivas)."""
    argv = build_docker_command(policy, workspace_dir, command)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.warning("sandbox.docker: binário docker não encontrado no sistema")
        return SandboxResult(
            stdout="",
            stderr="Error: Docker não está instalado neste sistema — sandbox indisponível.",
            exit_code=127,
        )
    except PermissionError:
        logger.warning("sandbox.docker: sem permissão para executar o binário docker")
        return SandboxResult(
            stdout="",
            stderr="Error: sem permissão para executar docker — sandbox indisponível.",
            exit_code=126,
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
