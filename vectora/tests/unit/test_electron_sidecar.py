"""Electron sidecar (Fase 1, revisão) — spawn/readiness/shutdown do
Electron de dentro do lifespan do FastAPI.

Mesmo padrão de sidecar que `backend/scheduling/nats_sidecar.py` já usa
pro `nats-server`: resolve o binário, sobe via `asyncio.create_subprocess_exec`
dentro do event loop já rodando, encerra limpo, reusa processo já vivo. Sem
o build de dev do Electron disponível, degrada pra `None` sem lançar — o
backend segue de pé sem janela.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import electron_sidecar


@pytest.fixture(autouse=True)
def _reset_sidecar_state():
    electron_sidecar._proc = None
    electron_sidecar._spawn_lock = None
    electron_sidecar._log_task = None
    yield
    electron_sidecar._proc = None
    electron_sidecar._spawn_lock = None
    electron_sidecar._log_task = None


# ---------------------------------------------------------------------------
# should_spawn_electron — a decisão
# ---------------------------------------------------------------------------


class TestShouldSpawnElectron:
    def test_ja_sob_electron_retorna_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("VECTORA_DESKTOP", "1")
        assert electron_sidecar.should_spawn_electron() is False

    def test_headless_retorna_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("VECTORA_DESKTOP", raising=False)
        monkeypatch.setenv("VECTORA_HEADLESS", "1")
        assert electron_sidecar.should_spawn_electron() is False

    def test_sem_display_retorna_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("VECTORA_DESKTOP", raising=False)
        monkeypatch.delenv("VECTORA_HEADLESS", raising=False)
        with patch("backend.services.electron_sidecar.has_display", return_value=False):
            assert electron_sidecar.should_spawn_electron() is False

    def test_sem_build_de_dev_retorna_false(self, monkeypatch: pytest.MonkeyPatch):
        # Par de erro/edge case: display disponível mas Electron não
        # buildado (scons frontend não rodou) — não trava, só diz não.
        monkeypatch.delenv("VECTORA_DESKTOP", raising=False)
        monkeypatch.delenv("VECTORA_HEADLESS", raising=False)
        with (
            patch("backend.services.electron_sidecar.has_display", return_value=True),
            patch(
                "backend.services.electron_sidecar.resolve_electron_launch",
                return_value=None,
            ),
        ):
            assert electron_sidecar.should_spawn_electron() is False

    def test_tudo_disponivel_retorna_true(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("VECTORA_DESKTOP", raising=False)
        monkeypatch.delenv("VECTORA_HEADLESS", raising=False)
        with (
            patch("backend.services.electron_sidecar.has_display", return_value=True),
            patch(
                "backend.services.electron_sidecar.resolve_electron_launch",
                return_value=("electron.exe", ["main.js"]),
            ),
        ):
            assert electron_sidecar.should_spawn_electron() is True


# ---------------------------------------------------------------------------
# ensure_electron_sidecar / stop_electron_sidecar — spawn mockado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_electron_sidecar_retorna_none_sem_build_resolvido():
    with patch(
        "backend.services.electron_sidecar.resolve_electron_launch",
        return_value=None,
    ):
        proc = await electron_sidecar.ensure_electron_sidecar()

    assert proc is None
    assert electron_sidecar._proc is None


@pytest.mark.asyncio
async def test_ensure_electron_sidecar_spawna_e_guarda_o_processo():
    fake_proc = MagicMock()
    fake_proc.pid = 4242
    fake_proc.returncode = None
    fake_proc.stdout = None  # sem stream real — pipe_to_logger vira no-op

    with (
        patch(
            "backend.services.electron_sidecar.resolve_electron_launch",
            return_value=("electron.exe", ["main.js"]),
        ),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=fake_proc),
        ) as spawn_mock,
    ):
        proc = await electron_sidecar.ensure_electron_sidecar()

    assert proc is fake_proc
    assert electron_sidecar._proc is fake_proc
    spawn_mock.assert_called_once()
    call_args, call_kwargs = spawn_mock.call_args
    assert call_args == ("electron.exe", "main.js")
    assert call_kwargs["env"]["VECTORA_EXTERNAL_BACKEND"] == "1"
    assert call_kwargs["stdout"] == asyncio.subprocess.PIPE
    assert call_kwargs["stderr"] == asyncio.subprocess.STDOUT
    # dá um tick pro _log_task (pipe_to_logger com stdout=None) rodar e
    # retornar de imediato, sem deixar task/warning pendurado.
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_ensure_electron_sidecar_reusa_processo_ja_rodando():
    fake_proc = MagicMock()
    fake_proc.returncode = None
    electron_sidecar._proc = fake_proc

    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as spawn_mock:
        proc = await electron_sidecar.ensure_electron_sidecar()

    assert proc is fake_proc
    spawn_mock.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_electron_sidecar_falha_de_spawn_retorna_none_sem_lancar():
    # Par de erro: binário corrompido/permissão negada não propaga —
    # o backend segue de pé sem janela.
    with (
        patch(
            "backend.services.electron_sidecar.resolve_electron_launch",
            return_value=("electron.exe", ["main.js"]),
        ),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=OSError("binário corrompido")),
        ),
    ):
        proc = await electron_sidecar.ensure_electron_sidecar()

    assert proc is None
    assert electron_sidecar._proc is None


@pytest.mark.asyncio
async def test_stop_electron_sidecar_termina_e_limpa_estado():
    fake_proc = MagicMock()
    fake_proc.returncode = None
    fake_proc.terminate = MagicMock()
    fake_proc.wait = AsyncMock(return_value=None)
    electron_sidecar._proc = fake_proc

    await electron_sidecar.stop_electron_sidecar()

    fake_proc.terminate.assert_called_once()
    assert electron_sidecar._proc is None


@pytest.mark.asyncio
async def test_stop_electron_sidecar_sem_processo_e_noop():
    await electron_sidecar.stop_electron_sidecar()
    assert electron_sidecar._proc is None
