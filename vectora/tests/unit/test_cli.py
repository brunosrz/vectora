"""Tests — CLI operacional (backend/cli) e parser do main.

Cobre o parser pós-remoção do TUI (sem chat/server, com start/config) e os
comandos novos de operação (config keys/docker/qdrant/redis), com 1 happy + 1
erro por comando conforme o padrão de TDD do projeto.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from rich.console import Console as _Console

from backend.cli import infra, keys
from backend.main import _build_parser


def _null_console(*_a: object, **_kw: object) -> _Console:
    return _Console(file=io.StringIO())


# ---------------------------------------------------------------------------
# Parser — TUI removido, start/config presentes
# ---------------------------------------------------------------------------


def test_parser_sem_subcomando_nao_define_command():
    parser = _build_parser()
    args = parser.parse_args([])
    assert getattr(args, "command", None) is None


def test_parser_remove_chat_e_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stderr", io.StringIO())
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["chat"])
    with pytest.raises(SystemExit):
        parser.parse_args(["server", "web"])


def test_parser_start_headless_e_porta():
    parser = _build_parser()
    args = parser.parse_args(["start", "--headless", "--port", "9000"])
    assert args.command == "start"
    assert args.headless is True
    assert args.port == 9000


def test_parser_config_keys_docker_qdrant_redis():
    parser = _build_parser()
    assert parser.parse_args(["config", "keys"]).config_action == "keys"

    docker = parser.parse_args(["config", "docker", "up"])
    assert docker.config_action == "docker"
    assert docker.config_arg == "up"

    qdrant = parser.parse_args(
        ["config", "qdrant", "https://q.example", "--api-key", "k"]
    )
    assert qdrant.config_action == "qdrant"
    assert qdrant.config_arg == "https://q.example"
    assert qdrant.api_key == "k"

    redis = parser.parse_args(["config", "redis", "redis://localhost:6379/0"])
    assert redis.config_action == "redis"
    assert redis.config_arg == "redis://localhost:6379/0"


def test_parser_config_sem_acao_aceita_set():
    parser = _build_parser()
    args = parser.parse_args(["config", "--set", "verbosity=2"])
    assert args.config_action is None
    assert args.set_values == ["verbosity=2"]


# ---------------------------------------------------------------------------
# keys.upsert_env_key — escreve e atualiza idempotente
# ---------------------------------------------------------------------------


def test_upsert_env_key_insere_e_atualiza(tmp_path: Path):
    env = tmp_path / ".env"

    keys.upsert_env_key(env, "FOO", "1")
    assert "FOO=1" in env.read_text(encoding="utf-8")

    keys.upsert_env_key(env, "BAR", "2")
    body = env.read_text(encoding="utf-8")
    assert "FOO=1" in body
    assert "BAR=2" in body

    # Atualização: FOO muda de valor sem duplicar a linha.
    keys.upsert_env_key(env, "FOO", "9")
    body = env.read_text(encoding="utf-8")
    assert "FOO=9" in body
    assert "FOO=1" not in body
    assert body.count("FOO=") == 1


# ---------------------------------------------------------------------------
# infra.run_docker — happy (ok) e erro (not ok → SystemExit)
# ---------------------------------------------------------------------------


def test_run_docker_status_ok(monkeypatch, capsys):
    from backend.storage.dev_stack import StackResult

    monkeypatch.setattr(
        "backend.storage.dev_stack.stack_status",
        lambda: StackResult(ok=True, messages=["vectora-postgres: rodando"]),
    )
    infra.run_docker("status")
    assert "rodando" in capsys.readouterr().out


def test_run_docker_falha_sai_com_erro(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.storage.dev_stack import StackResult

    monkeypatch.setattr("backend.cli.infra.Console", _null_console)
    monkeypatch.setattr(
        "backend.storage.dev_stack.stack_up",
        lambda: StackResult(ok=False, messages=["Docker não encontrado"]),
    )
    with pytest.raises(SystemExit):
        infra.run_docker("up")


# ---------------------------------------------------------------------------
# infra.run_qdrant / run_redis — happy (persiste) e erro (conexão falha)
# ---------------------------------------------------------------------------


def test_run_qdrant_ok_persiste_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from backend.workspace import runtime_settings as rs_module
    from backend.workspace.runtime_settings import RuntimeSettings

    monkeypatch.setattr("backend.cli.infra.Console", _null_console)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    fresh = RuntimeSettings(path=tmp_path / "checkpoints.db")
    monkeypatch.setattr(rs_module, "runtime_settings", fresh)

    async def _ok(url: str, api_key: str | None) -> None:
        return None

    monkeypatch.setattr(infra, "_test_qdrant", _ok)
    infra.run_qdrant("https://q.example", "secret")

    env = (tmp_path / ".vectora" / ".env").read_text(encoding="utf-8")
    assert "QDRANT_URL=https://q.example" in env
    assert "QDRANT_API_KEY=secret" in env
    # storage_mode agora vive em app_settings (SQLite), não no .env.
    assert fresh.storage_mode == "complete"


def test_run_qdrant_sem_url_sai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.cli.infra.Console", _null_console)
    with pytest.raises(SystemExit):
        infra.run_qdrant("", None)


def test_run_redis_falha_conexao_sai(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("backend.cli.infra.Console", _null_console)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    async def _boom(url: str) -> None:
        raise ConnectionError("recusado")

    monkeypatch.setattr(infra, "_test_redis", _boom)
    with pytest.raises(SystemExit):
        infra.run_redis("redis://localhost:6379/0")
