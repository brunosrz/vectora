"""Configuração compartilhada por toda a suíte Python (escopo ``tests/``).

⚠️ Rede de segurança contra travamento no shutdown — a CI não finalizava.

Sintoma: o pytest reportava o resultado final ("N passed") e gravava o
``coverage.xml`` normalmente, mas o **processo nunca saía**. O job da CI ficava
horas parado na tela de resultado até ser cancelado manualmente.

Causa: alguns recursos exercitados nos testes deixam **threads não-daemon**
vivas (ex.: o ``Observer`` do watchdog usado no SSE de eventos de workspace,
quando o stream de um teste não é drenado e o ``finally`` que faz
``observer.stop()`` nunca roda). Quando o pytest termina, o CPython chama
``threading._shutdown()``, que faz ``join`` em todas as threads não-daemon —
e fica bloqueado para sempre numa thread que nunca encerra. O resultado já foi
impresso; o interpretador apenas não consegue sair.

Correção: em ``pytest_unconfigure`` — que roda DEPOIS do summary e da gravação
do coverage — registramos (diagnóstico) as threads remanescentes e encerramos
o processo com ``os._exit(code)``, preemptando o ``join`` travado. O código de
saída é preservado, então a CI continua detectando falhas corretamente.

O ideal é também não vazar a thread (ver ``src/api/handlers/workspaces.py``,
onde o observer agora é ``daemon``), mas esta rede garante que NENHUM vazamento
futuro volte a travar o pipeline.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    import git as gitpython

# Capturado em pytest_sessionfinish e usado no pytest_unconfigure: o
# unconfigure não recebe o exitstatus, então guardamos aqui.
_exit_status: int = 0

_REPO_ROOT = Path(__file__).resolve().parent.parent


def pytest_sessionfinish(exitstatus: int) -> None:
    """Memoriza o código de saída final para o pytest_unconfigure.

    O pytest injeta apenas os argumentos do hook que declaramos pelo nome —
    por isso pedimos só ``exitstatus`` (o ``session`` não é necessário aqui).
    """
    global _exit_status
    _exit_status = int(exitstatus)


def pytest_unconfigure(config: Any) -> None:
    """Força o término do processo após o pytest concluir todo o relatório.

    Roda no fim do ciclo do pytest, depois que o summary e o coverage já foram
    emitidos — antes do ``threading._shutdown()`` que travaria no join.
    """
    # Em workers do pytest-xdist NÃO forçamos o exit: quebraria o protocolo de
    # coleta de resultados do processo controlador. Só o principal encerra.
    if hasattr(config, "workerinput"):
        return

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_exit_status)


# ============================================================================
# Backend real spawnado como subprocesso — fica na raiz (não em
# tests/integration/conftest.py) porque também é usado por tests/e2e/
# (test_agent_live_runs.py), que não é subárvore de tests/integration/.
# ============================================================================


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_port_open(port: int, timeout_s: float) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout_s
    last_error: OSError | None = None
    while loop.time() < deadline:
        try:
            _, writer = await asyncio.open_connection("127.0.0.1", port)
        except OSError as exc:
            last_error = exc
            await asyncio.sleep(0.2)
            continue
        writer.close()
        await writer.wait_closed()
        return
    raise TimeoutError(
        f"porta {port} não abriu em {timeout_s}s (último erro: {last_error})"
    )


async def _drain(stream: asyncio.StreamReader | None) -> None:
    """Consome stdout/stderr do processo pra não travar o pipe do SO."""
    if stream is None:
        return
    while not stream.at_eof():
        await stream.read(4096)


_background_tasks: set[asyncio.Task[None]] = set()


def _track(task: asyncio.Task[None]) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@pytest.fixture(autouse=True)
def _isolate_native_tool_registry() -> Generator[None]:
    """``backend.tools.registry.TOOL_REGISTRY`` é um singleton de processo —
    vários testes definem tools locais via ``@vtool`` com o mesmo nome (ex.
    ``buscar``, repetido em test_*_chat_client.py e test_engine_conversation_
    loop.py). Sem isolamento, rodar a suíte inteira num processo só colide
    ("tool já registrada") mesmo com cada teste passando isolado. Snapshot +
    restore em vez de ``clear()`` — preserva qualquer tool que um módulo de
    produção venha a registrar de verdade no import (hoje nenhum, mas não
    assume isso pra sempre)."""
    from backend.tools.registry import TOOL_REGISTRY

    snapshot = dict(TOOL_REGISTRY._tools)
    yield
    TOOL_REGISTRY._tools.clear()
    TOOL_REGISTRY._tools.update(snapshot)


@pytest.fixture
async def spawned_backend(tmp_path: Path):
    """Backend real (``python -m backend.main start``) rodando num
    ``VECTORA_HOME`` isolado — mesmo caminho de processo que o Electron usa
    em produção. Não exige ``frontend/dist`` (diferente de
    ``_spawned_backend`` em ``test_frontend_served_lifecycle.py``, que serve
    estático — este fixture é pra exercitar a API real via HTTP).

    Yields ``(base_url, port)``.
    """
    port = _free_port()
    env = dict(os.environ)
    env["VECTORA_HOME"] = str(tmp_path)
    env["VECTORA_DESKTOP"] = "1"
    env["VECTORA_UVICORN_LOG_LEVEL"] = "warning"
    env["VECTORA_SKIP_STATIC"] = "1"

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "backend.main",
        "start",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _track(asyncio.create_task(_drain(proc.stdout)))
    _track(asyncio.create_task(_drain(proc.stderr)))
    try:
        await _wait_port_open(port, timeout_s=60.0)
        yield f"http://127.0.0.1:{port}", port
    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=10.0)
            except TimeoutError:
                proc.kill()
                await proc.wait()


# ============================================================================
# Git repo + workspace reais — reutilizável por qualquer teste que precise
# de um repositório git de verdade (evita `git.Repo.init` inline repetido).
# ============================================================================


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> gitpython.Repo:
    """Repositório git real, com um commit inicial (`README.md`), pronto
    para os testes exercitarem status/diff/branch/worktree de verdade."""
    import git as gitpython

    repo = gitpython.Repo.init(tmp_path)
    with repo.config_writer() as cfg:
        cfg.set_value("user", "name", "Vectora Test")
        cfg.set_value("user", "email", "test@vectora.chat")
    readme = tmp_path / "README.md"
    readme.write_text("# test repo\n", encoding="utf-8")
    repo.index.add([str(readme)])
    repo.index.commit("initial commit")
    return repo


@pytest.fixture
def real_workspace(tmp_git_repo: gitpython.Repo, tmp_path: Path) -> Generator[str]:
    """Registra `tmp_git_repo` no `workspace_registry` real e devolve o
    `workspace_id` — usado por testes que exercitam handlers/tools que
    resolvem workspace_id -> path via o registry de verdade."""
    from backend.workspace.workspace import workspace_registry

    ws = workspace_registry.get_or_create(str(tmp_path))
    try:
        yield ws.id
    finally:
        workspace_registry.delete(ws.id)
