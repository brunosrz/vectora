"""NATS sidecar (D3) — spawn/readiness/shutdown do backend Python.

Mesmo padrão de sidecar que o Electron já usa pro backend Python
(resolve o binário, escolhe porta livre, lê stdout até o sinal de "pronto",
encerra limpo) — aqui é o próprio backend que sobe o nats-server, um nível
abaixo. Sem o binário disponível (dev sem instalação local, CI), degrada
pra None sem lançar — get_mq()/get_kv() caem pro fallback em memória.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.scheduling import nats_sidecar


@pytest.fixture(autouse=True)
def _reset_sidecar_state(tmp_path, monkeypatch):
    # `Path.home()` isolado por padrão em TODO teste deste arquivo — sem
    # isso, qualquer teste que não pense em PID file acaba lendo/escrevendo
    # o ~/.vectora/nats real do dev (um pid file real deixado por uma
    # execução anterior faria `ensure_nats_sidecar()` chamar `_pid_is_alive`
    # contra um PID de verdade, tornando o teste dependente do disco do
    # host). Testes de `TestOrphanPidFile` pedem `tmp_path` de novo — é a
    # MESMA instância (cache por teste do pytest), então ficam coerentes.
    monkeypatch.setattr(nats_sidecar.settings, "vectora_home", tmp_path)

    nats_sidecar._proc = None
    nats_sidecar._url = None
    nats_sidecar._log_task = None
    yield
    if nats_sidecar._log_task is not None:
        nats_sidecar._log_task.cancel()
    nats_sidecar._proc = None
    nats_sidecar._url = None
    nats_sidecar._log_task = None


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_returns_none_when_binary_not_found():
    with patch.object(nats_sidecar, "_resolve_binary", return_value=None):
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url is None
    assert nats_sidecar._proc is None


def test_resolve_binary_honra_override_env(tmp_path, monkeypatch):
    """VECTORA_NATS_BINARY (apontado pelo Electron pro binário empacotado) tem
    prioridade sobre PATH/resource, e só vale se o arquivo existir."""
    fake = tmp_path / "nats-server"
    fake.write_text("")  # arquivo existe

    monkeypatch.setenv("VECTORA_NATS_BINARY", str(fake))
    # Mesmo com um nats-server no PATH, o override vence.
    monkeypatch.setattr(nats_sidecar.shutil, "which", lambda _n: "/usr/bin/nats-server")
    assert nats_sidecar._resolve_binary() == str(fake)

    # Par de erro: override apontando pra arquivo inexistente é ignorado (cai
    # no PATH), nunca devolve um caminho quebrado.
    monkeypatch.setenv("VECTORA_NATS_BINARY", str(tmp_path / "nao-existe"))
    assert nats_sidecar._resolve_binary() == "/usr/bin/nats-server"


def test_resolve_binary_usa_bundle_pyinstaller_antes_do_path(tmp_path, monkeypatch):
    """No binário congelado (build-hybrid.py empacota vectora/resources/
    nats-server via PyInstaller --add-binary em ``nats/``), sys._MEIPASS deve
    vencer o PATH — senão um nats-server desalinhado instalado na máquina do
    usuário (versão diferente da testada) seria usado em produção."""
    monkeypatch.delenv("VECTORA_NATS_BINARY", raising=False)
    nats_dir = tmp_path / "nats"
    nats_dir.mkdir()
    bundled = nats_dir / nats_sidecar._exe_name()
    bundled.write_text("")

    monkeypatch.setattr(nats_sidecar.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(nats_sidecar.shutil, "which", lambda _n: "/usr/bin/nats-server")

    assert nats_sidecar._resolve_binary() == str(bundled)


def test_resolve_binary_meipass_sem_arquivo_cai_no_path(tmp_path, monkeypatch):
    """Borda: _MEIPASS setado mas sem nats/nats-server dentro (build sem
    `scons nats` antes do PyInstaller) — não trava, degrada pro PATH."""
    monkeypatch.delenv("VECTORA_NATS_BINARY", raising=False)
    monkeypatch.setattr(nats_sidecar.sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(nats_sidecar.shutil, "which", lambda _n: "/usr/bin/nats-server")

    assert nats_sidecar._resolve_binary() == "/usr/bin/nats-server"


def test_resolve_binary_usa_nuitka_compiled_containing_dir(tmp_path, monkeypatch):
    """Onefile Nuitka expõe sys.__compiled__.containing_dir — mesma resolução
    usada por server.py::_chat_static_root para o bundle do frontend."""
    monkeypatch.delenv("VECTORA_NATS_BINARY", raising=False)
    monkeypatch.delattr(nats_sidecar.sys, "_MEIPASS", raising=False)
    nats_dir = tmp_path / "nats"
    nats_dir.mkdir()
    bundled = nats_dir / nats_sidecar._exe_name()
    bundled.write_text("")

    fake_compiled = type("FakeCompiled", (), {"containing_dir": str(tmp_path)})()
    monkeypatch.setattr(nats_sidecar.sys, "__compiled__", fake_compiled, raising=False)
    monkeypatch.setattr(nats_sidecar.shutil, "which", lambda _n: None)

    assert nats_sidecar._resolve_binary() == str(bundled)


def _fake_ready_proc(ready_line: bytes = b"Server is ready\n") -> MagicMock:
    proc = MagicMock()
    # Depois da linha de "ready", EOF — sem isso a task de background
    # `pipe_to_logger` (criada após o handshake) ficaria lendo a mesma
    # linha pra sempre, um loop infinito consumindo CPU no teste.
    proc.stdout.readline = AsyncMock(side_effect=[ready_line, b""])
    proc.returncode = None
    proc.kill = MagicMock()
    return proc


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_spawns_and_returns_url_when_ready():
    fake_proc = _fake_ready_proc()

    with (
        patch.object(
            nats_sidecar, "_resolve_binary", return_value="/usr/bin/nats-server"
        ),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=fake_proc),
        ),
    ):
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url is not None
    assert url.startswith("nats://127.0.0.1:")
    assert nats_sidecar._proc is fake_proc


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_kills_process_and_returns_none_when_not_ready():
    """Edge — processo sobe mas nunca emite "Server is ready" (porta ocupada etc.)."""
    never_ready_proc = MagicMock()
    never_ready_proc.stdout.readline = AsyncMock(return_value=b"")  # EOF imediato
    never_ready_proc.kill = MagicMock()

    with (
        patch.object(
            nats_sidecar, "_resolve_binary", return_value="/usr/bin/nats-server"
        ),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=never_ready_proc),
        ),
    ):
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url is None
    never_ready_proc.kill.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_reuses_running_process():
    fake_proc = _fake_ready_proc()
    nats_sidecar._proc = fake_proc
    nats_sidecar._url = "nats://127.0.0.1:4222"

    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as spawn_mock:
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url == "nats://127.0.0.1:4222"
    spawn_mock.assert_not_called()


@pytest.mark.asyncio
async def test_stop_nats_sidecar_terminates_and_clears_state():
    fake_proc = MagicMock()
    fake_proc.terminate = MagicMock()
    fake_proc.wait = AsyncMock(return_value=None)
    nats_sidecar._proc = fake_proc
    nats_sidecar._url = "nats://127.0.0.1:4222"

    await nats_sidecar.stop_nats_sidecar()

    fake_proc.terminate.assert_called_once()
    assert nats_sidecar._proc is None
    assert nats_sidecar.current_url() is None


@pytest.mark.asyncio
async def test_stop_nats_sidecar_without_running_process_is_noop():
    await nats_sidecar.stop_nats_sidecar()
    assert nats_sidecar._proc is None


class TestOrphanPidFile:
    """D3 tinha um bug real: cada novo processo Python (nova sessão `vectora
    start`, ou pytest rodado de novo) não sabe de sidecars órfãos deixados por
    uma sessão anterior que morreu sem passar pelo shutdown gracioso (kill
    forçado, crash, fechar o terminal) — resultado observado em produção:
    dezenas de `nats-server.exe` acumulados. Um PID file cross-processo
    resolve: antes de spawnar, mata qualquer órfão vivo registrado."""

    def test_pid_file_path_fica_dentro_do_store_dir(self, tmp_path):
        assert nats_sidecar._pid_file_path(tmp_path) == tmp_path / "sidecar.pid"

    def test_write_e_read_pid_file_roundtrip(self, tmp_path):
        nats_sidecar._write_pid_file(tmp_path, 4242)
        assert nats_sidecar._read_stale_pid(tmp_path) == 4242

    def test_read_stale_pid_sem_arquivo_retorna_none(self, tmp_path):
        assert nats_sidecar._read_stale_pid(tmp_path) is None

    def test_read_stale_pid_arquivo_corrompido_retorna_none(self, tmp_path):
        # Erro/borda: JSON inválido ou campo ausente nunca derruba o caller —
        # degrada pra "nenhum pid conhecido" (fail-safe, não fail-open pra
        # matar processo errado).
        (tmp_path / "sidecar.pid").write_text("{nao e json valido", encoding="utf-8")
        assert nats_sidecar._read_stale_pid(tmp_path) is None

    def test_clear_pid_file_remove_e_e_idempotente(self, tmp_path):
        nats_sidecar._write_pid_file(tmp_path, 4242)
        nats_sidecar._clear_pid_file(tmp_path)
        assert not (tmp_path / "sidecar.pid").is_file()
        nats_sidecar._clear_pid_file(tmp_path)  # segunda chamada não lança

    @pytest.mark.asyncio
    async def test_ensure_nats_sidecar_mata_orfao_registrado_antes_de_spawnar(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(nats_sidecar.settings, "vectora_home", tmp_path)
        store_dir = tmp_path / "nats"
        store_dir.mkdir(parents=True)
        nats_sidecar._write_pid_file(store_dir, 9999)

        fake_proc = _fake_ready_proc()
        fake_proc.pid = 12345
        kill_mock = MagicMock()

        with (
            patch.object(
                nats_sidecar, "_resolve_binary", return_value="/usr/bin/nats-server"
            ),
            patch.object(nats_sidecar, "_pid_is_alive", return_value=True),
            patch.object(nats_sidecar, "_kill_pid", kill_mock),
            patch(
                "asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake_proc)
            ),
        ):
            url = await nats_sidecar.ensure_nats_sidecar()

        kill_mock.assert_called_once_with(9999)
        assert url is not None
        # Órfão morto e substituído — o pid file agora aponta pro processo novo.
        assert nats_sidecar._read_stale_pid(store_dir) == 12345

    @pytest.mark.asyncio
    async def test_ensure_nats_sidecar_ignora_pid_morto_sem_tentar_matar(
        self, tmp_path, monkeypatch
    ):
        # Par de erro/borda: pid file existe mas o processo já morreu sozinho
        # (ex.: crash) — não deve chamar kill à toa, só limpar e seguir.
        monkeypatch.setattr(nats_sidecar.settings, "vectora_home", tmp_path)
        store_dir = tmp_path / "nats"
        store_dir.mkdir(parents=True)
        nats_sidecar._write_pid_file(store_dir, 9999)

        fake_proc = _fake_ready_proc()
        fake_proc.pid = 12345
        kill_mock = MagicMock()

        with (
            patch.object(
                nats_sidecar, "_resolve_binary", return_value="/usr/bin/nats-server"
            ),
            patch.object(nats_sidecar, "_pid_is_alive", return_value=False),
            patch.object(nats_sidecar, "_kill_pid", kill_mock),
            patch(
                "asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake_proc)
            ),
        ):
            await nats_sidecar.ensure_nats_sidecar()

        kill_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_nats_sidecar_limpa_o_pid_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(nats_sidecar.settings, "vectora_home", tmp_path)
        store_dir = tmp_path / "nats"
        store_dir.mkdir(parents=True)
        nats_sidecar._write_pid_file(store_dir, 4242)

        fake_proc = MagicMock()
        fake_proc.terminate = MagicMock()
        fake_proc.wait = AsyncMock(return_value=None)
        nats_sidecar._proc = fake_proc
        nats_sidecar._url = "nats://127.0.0.1:4222"

        await nats_sidecar.stop_nats_sidecar()

        assert nats_sidecar._read_stale_pid(store_dir) is None
