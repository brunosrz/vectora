"""Backend de sandbox via Modal (sandbox cloud sob demanda) — via SDK
oficial `modal`. Opt-in e com custo externo (billing por uso) — nunca o
default; só ativa quando `vectora.toml` declara `backend = "modal"`
explicitamente.

API usada (`modal.Sandbox.create` / `.exec` / `ContainerProcess`):
https://modal.com/docs/guide/sandbox-spawn
"""

from __future__ import annotations

import asyncio
import logging

from backend.sandbox.linux import SandboxResult
from backend.sandbox.policy import SandboxPolicy

logger = logging.getLogger(__name__)


async def run_modal_sandboxed(
    command: list[str],
    workspace_dir: str,
    policy: SandboxPolicy,
    *,
    timeout_s: float = 60.0,
) -> SandboxResult:
    """Roda `command` num Modal Sandbox efêmero. Sem o SDK instalado ou sem
    credenciais configuradas, degrada com mensagem clara oferecendo os
    outros backends — nunca trava o caller nem cai silenciosamente pro
    processo local (fail-closed: o usuário pediu 'modal' explicitamente).

    `workspace_dir`/`policy` (exceto o comando em si) não são usados ainda:
    diferente de `local`/`docker`/`ssh`, o Modal Sandbox roda num
    filesystem cloud isolado, não um bind-mount do workspace local — subir
    o conteúdo do workspace pra lá (via `modal.Volume`) fica pra quando
    este backend tiver uso real, não faz sentido implementar às cegas.
    """
    del workspace_dir, policy
    try:
        import modal  # ty: ignore[unresolved-import]
    except ImportError:
        return SandboxResult(
            stdout="",
            stderr=(
                "Error: pacote 'modal' não instalado — backend 'modal' "
                "indisponível. Instale com `pip install modal` ou use "
                "backend 'local', 'docker' ou 'ssh'."
            ),
            exit_code=127,
        )

    def _run_sync() -> tuple[str, str, int]:
        app = modal.App.lookup("vectora-sandbox", create_if_missing=True)
        sb = modal.Sandbox.create(app=app)
        try:
            process = sb.exec(*command, timeout=int(timeout_s))
            exit_code = process.wait()
            stdout = process.stdout.read()
            stderr = process.stderr.read()
            return stdout, stderr, exit_code
        finally:
            sb.terminate()

    try:
        stdout, stderr, exit_code = await asyncio.wait_for(
            asyncio.to_thread(_run_sync), timeout=timeout_s + 10.0
        )
        return SandboxResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
    except TimeoutError:
        return SandboxResult(
            stdout="",
            stderr=f"Error: comando excedeu o timeout de {timeout_s}s.",
            exit_code=124,
            timed_out=True,
        )
    except Exception as exc:
        logger.warning("sandbox.modal: falha (%s)", exc)
        return SandboxResult(
            stdout="",
            stderr=(
                f"Error: falha no Modal ({exc}). Verifique credenciais "
                "(modal token) ou use outro backend."
            ),
            exit_code=125,
        )
