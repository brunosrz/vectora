"""Testes do dev_stack — defaults de infra local e comandos docker.

Garante que:
- as URLs default (defaults.env) batem com as constantes do dev_stack;
- os specs dos serviços usam as mesmas imagens do docker-compose.yml;
- o probe redis_reachable faz get_kv/get_mq caírem para memória quando o
  redis_url default está setado mas o serviço não está de pé.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.storage.dev_stack import (
    DEFAULT_POSTGRES_DSN,
    DEFAULT_QDRANT_API_KEY,
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
    defaults = (REPO_ROOT / "backend" / "defaults.env").read_text(encoding="utf-8")
    assert f"POSTGRES_DSN={DEFAULT_POSTGRES_DSN}" in defaults
    assert f"REDIS_URL={DEFAULT_REDIS_URL}" in defaults
    assert f"QDRANT_URL={DEFAULT_QDRANT_URL}" in defaults
    assert f"QDRANT_API_KEY={DEFAULT_QDRANT_API_KEY}" in defaults


def test_nenhum_servico_sem_credencial() -> None:
    """Auth em todos os serviços, mesmo em dev — Redis com senha na URL
    (mesmo formato do Postgres) e Qdrant com API key."""
    assert "redis://:" in DEFAULT_REDIS_URL  # senha embutida (redis://:senha@host)
    assert DEFAULT_QDRANT_API_KEY
    redis = next(s for s in SERVICES if s.name == "vectora-redis")
    assert "--requirepass" in redis.command
    qdrant = next(s for s in SERVICES if s.name == "vectora-qdrant")
    assert any(e.startswith("QDRANT__SERVICE__API_KEY=") for e in qdrant.env)


def test_portas_publicadas_apenas_em_localhost() -> None:
    for spec in SERVICES:
        for port in spec.ports:
            assert port.startswith("127.0.0.1:"), (
                f"{spec.name}: porta {port} exposta além de localhost"
            )


def test_settings_carregam_defaults_de_infra(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sem env explícito, os defaults embarcados devem preencher os campos.
    for key in ("POSTGRES_DSN", "REDIS_URL", "QDRANT_URL", "QDRANT_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    from backend.settings import Settings

    s = Settings()
    assert s.postgres_dsn == DEFAULT_POSTGRES_DSN
    assert s.redis_url == DEFAULT_REDIS_URL
    assert s.qdrant_url == DEFAULT_QDRANT_URL
    assert s.qdrant_api_key == DEFAULT_QDRANT_API_KEY


def test_specs_usam_imagens_compativeis_com_compose() -> None:
    """Postgres e Qdrant usam a mesma imagem no dev_stack e no docker-compose.yml.

    O Redis diverge de propósito: o dev_stack usa a imagem leve; o compose usa
    redis-stack-server porque o cache LLM (langchain-redis) precisa de
    RediSearch/RedisJSON. Sem esses módulos o cache cai para InMemoryCache.
    """
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for name in ("vectora-postgres", "vectora-qdrant"):
        spec = next(s for s in SERVICES if s.name == name)
        assert spec.image in compose, f"imagem {spec.image} divergiu do compose"
    assert "redis/redis-stack-server" in compose


def test_connection_urls_mapeia_constantes() -> None:
    urls = connection_urls()
    assert urls == {
        "POSTGRES_DSN": DEFAULT_POSTGRES_DSN,
        "REDIS_URL": DEFAULT_REDIS_URL,
        "QDRANT_URL": DEFAULT_QDRANT_URL,
        "QDRANT_API_KEY": DEFAULT_QDRANT_API_KEY,
    }


# ---------------------------------------------------------------------------
# docker run — estrutura dos comandos
# ---------------------------------------------------------------------------


def test_docker_run_cmd_postgres() -> None:
    spec = next(s for s in SERVICES if s.name == "vectora-postgres")
    cmd = docker_run_cmd(spec)
    assert cmd[:3] == ["docker", "run", "-d"]
    assert "--name" in cmd and "vectora-postgres" in cmd
    assert "-p" in cmd and "127.0.0.1:5432:5432" in cmd
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
        "--requirepass",
        "vectora",
    ]


def test_parser_aceita_storage_up_down() -> None:
    from backend.main import _build_parser

    parser = _build_parser()
    assert parser.parse_args(["storage", "up"]).action == "up"
    assert parser.parse_args(["storage", "down"]).action == "down"


# ---------------------------------------------------------------------------
# Probe de conectividade — fallback para memória com redis fora do ar
# ---------------------------------------------------------------------------


@pytest.fixture
def _reset_singletons():
    from backend.services.kv import reset_kv, reset_reachable_cache
    from backend.services.mq import reset_mq

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
    from backend.services.kv import MemoryKV, get_kv
    from backend.settings import settings

    # Porta 9 (discard) — nada escutando; probe deve falhar rápido.
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:9/0")
    assert isinstance(get_kv(), MemoryKV)


def test_get_mq_cai_para_memoria_com_redis_inacessivel(
    monkeypatch: pytest.MonkeyPatch, _reset_singletons
) -> None:
    from backend.services.mq import MemoryMQ, get_mq
    from backend.settings import settings

    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:9/0")
    assert isinstance(get_mq(), MemoryMQ)


def test_redis_reachable_cacheia_resultado(_reset_singletons) -> None:
    from backend.services import kv

    assert kv.redis_reachable("redis://127.0.0.1:9/0", timeout=0.1) is False
    assert "redis://127.0.0.1:9/0" in kv._reachable_cache
