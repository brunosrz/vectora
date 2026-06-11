"""Testes do dev_stack — defaults de infra local e comandos docker.

Garante que:
- as URLs default (defaults.env) batem com as constantes do dev_stack;
- os specs dos serviços espelham deploy/compose.dev.yml (imagens, portas,
  flags do redis-server);
- o probe redis_reachable faz get_kv/get_mq caírem para memória quando o
  redis_url default está setado mas o serviço não está de pé.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.storage.dev_stack import (
    DEFAULT_POSTGRES_DSN,
    DEFAULT_QDRANT_URL,
    DEFAULT_REDIS_URL,
    SERVICES,
    connection_urls,
    docker_run_cmd,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Consistência defaults.env ↔ dev_stack ↔ compose.dev.yml
# ---------------------------------------------------------------------------


def test_defaults_env_contem_urls_da_stack() -> None:
    defaults = (REPO_ROOT / "src" / "defaults.env").read_text(encoding="utf-8")
    assert f"POSTGRES_DSN={DEFAULT_POSTGRES_DSN}" in defaults
    assert f"REDIS_URL={DEFAULT_REDIS_URL}" in defaults
    assert f"QDRANT_URL={DEFAULT_QDRANT_URL}" in defaults


def test_settings_carregam_defaults_de_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sem env explícito, os defaults embarcados devem preencher os campos.
    for key in ("POSTGRES_DSN", "REDIS_URL", "QDRANT_URL"):
        monkeypatch.delenv(key, raising=False)
    from src.settings import Settings

    s = Settings()
    assert s.postgres_dsn == DEFAULT_POSTGRES_DSN
    assert s.redis_url == DEFAULT_REDIS_URL
    assert s.qdrant_url == DEFAULT_QDRANT_URL


def test_specs_espelham_compose_dev() -> None:
    compose = (REPO_ROOT / "deploy" / "compose.dev.yml").read_text(encoding="utf-8")
    for spec in SERVICES:
        assert spec.image in compose, f"imagem {spec.image} divergiu do compose"
        for port in spec.ports:
            assert f'"{port}"' in compose, f"porta {port} divergiu do compose"
    # Flags do redis-server idênticas às do compose
    redis = next(s for s in SERVICES if s.name == "vectora-redis")
    assert " ".join(redis.command) in compose


def test_connection_urls_mapeia_constantes() -> None:
    urls = connection_urls()
    assert urls == {
        "POSTGRES_DSN": DEFAULT_POSTGRES_DSN,
        "REDIS_URL": DEFAULT_REDIS_URL,
        "QDRANT_URL": DEFAULT_QDRANT_URL,
    }


# ---------------------------------------------------------------------------
# docker run — estrutura dos comandos
# ---------------------------------------------------------------------------


def test_docker_run_cmd_postgres() -> None:
    spec = next(s for s in SERVICES if s.name == "vectora-postgres")
    cmd = docker_run_cmd(spec)
    assert cmd[:3] == ["docker", "run", "-d"]
    assert "--name" in cmd and "vectora-postgres" in cmd
    assert "-p" in cmd and "5432:5432" in cmd
    assert "POSTGRES_USER=vectora" in cmd
    assert cmd[-1] == "pgvector/pgvector:pg16"  # sem command extra


def test_docker_run_cmd_redis_inclui_command() -> None:
    spec = next(s for s in SERVICES if s.name == "vectora-redis")
    cmd = docker_run_cmd(spec)
    image_idx = cmd.index("redis:7-alpine")
    assert cmd[image_idx + 1 :] == [
        "redis-server",
        "--appendonly",
        "yes",
        "--maxmemory",
        "256mb",
        "--maxmemory-policy",
        "allkeys-lru",
    ]


def test_parser_aceita_storage_up_down() -> None:
    from src.main import _build_parser

    parser = _build_parser()
    assert parser.parse_args(["storage", "up"]).action == "up"
    assert parser.parse_args(["storage", "down"]).action == "down"


# ---------------------------------------------------------------------------
# Probe de conectividade — fallback para memória com redis fora do ar
# ---------------------------------------------------------------------------


@pytest.fixture
def _reset_singletons():
    from src.services.kv import reset_kv, reset_reachable_cache
    from src.services.mq import reset_mq

    reset_kv()
    reset_mq()
    reset_reachable_cache()
    yield
    reset_kv()
    reset_mq()
    reset_reachable_cache()


def test_get_kv_cai_para_memoria_com_redis_inacessivel(
    monkeypatch: pytest.MonkeyPatch, _reset_singletons
) -> None:
    from src.services.kv import MemoryKV, get_kv
    from src.settings import settings

    # Porta 9 (discard) — nada escutando; probe deve falhar rápido.
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:9/0")
    assert isinstance(get_kv(), MemoryKV)


def test_get_mq_cai_para_memoria_com_redis_inacessivel(
    monkeypatch: pytest.MonkeyPatch, _reset_singletons
) -> None:
    from src.services.mq import MemoryMQ, get_mq
    from src.settings import settings

    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:9/0")
    assert isinstance(get_mq(), MemoryMQ)


def test_redis_reachable_cacheia_resultado(_reset_singletons) -> None:
    from src.services import kv

    assert kv.redis_reachable("redis://127.0.0.1:9/0", timeout=0.1) is False
    assert "redis://127.0.0.1:9/0" in kv._reachable_cache
