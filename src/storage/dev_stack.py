"""Stack local de infra — Postgres+pgvector, Redis e Qdrant via Docker.

Fonte única dos defaults de conexão e dos comandos `docker run` usados por
``vectora storage up``/``down``. Os valores espelham **exatamente** o
``deploy/compose.dev.yml`` (imagens, portas, volumes, env e command) — se o
compose mudar, este módulo deve mudar junto (teste de consistência em
``tests/unit/test_dev_stack.py``).

Estratégia do ``up``:
  1. Se o repo tem ``deploy/compose.dev.yml`` ao alcance (checkout de dev),
     usa ``docker compose -f ... up -d`` — comportamento idêntico ao README.
  2. Senão (instalação via wheel/pipx), sobe os 3 containers com
     ``docker run`` equivalentes, nomeados ``vectora-*`` e com volumes
     nomeados — reaproveitados em execuções futuras via ``docker start``.
"""

from __future__ import annotations

import logging
import subprocess  # nosec B404 — apenas comandos docker montados internamente
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Defaults de conexão (mesmos valores do defaults.env / compose.dev.yml) ──

DEFAULT_POSTGRES_DSN = "postgresql+asyncpg://vectora:vectora@localhost:5432/vectora"
DEFAULT_REDIS_URL = "redis://:vectora@localhost:6379/0"  # nosec B105 — dev local
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_API_KEY = "vectora"  # nosec B105 — dev local


@dataclass(frozen=True)
class ServiceSpec:
    """Um serviço da infra local — espelho 1:1 do compose.dev.yml."""

    name: str  # nome do container (vectora-*)
    image: str
    ports: tuple[str, ...]
    volumes: tuple[str, ...]
    env: tuple[str, ...] = ()
    command: tuple[str, ...] = ()


SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec(
        name="vectora-postgres",
        image="pgvector/pgvector:pg16",
        ports=("127.0.0.1:5432:5432",),
        volumes=("vectora-postgres:/var/lib/postgresql/data",),
        env=(
            "POSTGRES_USER=vectora",
            "POSTGRES_PASSWORD=vectora",  # nosec B105 — dev local, igual ao compose.dev.yml
            "POSTGRES_DB=vectora",
        ),
    ),
    ServiceSpec(
        name="vectora-redis",
        image="redis:7-alpine",
        ports=("127.0.0.1:6379:6379",),
        volumes=("vectora-redis:/data",),
        command=(
            "redis-server",
            "--appendonly",
            "yes",
            "--maxmemory",
            "256mb",
            "--maxmemory-policy",
            "allkeys-lru",
            "--requirepass",
            "vectora",
        ),
    ),
    ServiceSpec(
        name="vectora-qdrant",
        image="qdrant/qdrant:latest",
        ports=("127.0.0.1:6333:6333", "127.0.0.1:6334:6334"),
        volumes=("vectora-qdrant:/qdrant/storage",),
        env=(
            "QDRANT__SERVICE__GRPC_PORT=6334",
            "QDRANT__SERVICE__API_KEY=vectora",
        ),
    ),
)


def docker_run_cmd(spec: ServiceSpec) -> list[str]:
    """Monta o ``docker run`` equivalente ao serviço do compose.dev.yml."""
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        spec.name,
        "--restart",
        "unless-stopped",
    ]
    for port in spec.ports:
        cmd += ["-p", port]
    for env in spec.env:
        cmd += ["-e", env]
    for volume in spec.volumes:
        cmd += ["-v", volume]
    cmd.append(spec.image)
    cmd += list(spec.command)
    return cmd


def compose_file() -> Path | None:
    """Localiza deploy/compose.dev.yml relativo ao pacote (checkout de dev)."""
    candidate = (
        Path(__file__).resolve().parent.parent.parent / "deploy" / "compose.dev.yml"
    )
    return candidate if candidate.is_file() else None


# ── Execução ──────────────────────────────────────────────────────────────


@dataclass
class StackResult:
    ok: bool
    messages: list[str] = field(default_factory=list)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — comandos docker montados internamente  # nosec B603
        cmd, capture_output=True, text=True, timeout=180, check=False
    )


def _docker_available() -> bool:
    try:
        return (
            _run(["docker", "version", "--format", "{{.Server.Version}}"]).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def _existing_containers() -> set[str]:
    proc = _run(["docker", "ps", "-a", "--format", "{{.Names}}"])
    if proc.returncode != 0:
        return set()
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def stack_up() -> StackResult:
    """Sobe Postgres, Redis e Qdrant — compose quando disponível, docker run senão."""
    result = StackResult(ok=True)

    if not _docker_available():
        result.ok = False
        result.messages.append(
            "Docker não encontrado ou daemon parado. Instale/inicie o Docker "
            "Desktop (ou docker-ce) e tente de novo."
        )
        return result

    compose = compose_file()
    if compose is not None:
        proc = _run(["docker", "compose", "-f", str(compose), "up", "-d"])
        if proc.returncode == 0:
            result.messages.append(f"docker compose up -d ({compose})")
        else:
            result.ok = False
            result.messages.append(proc.stderr.strip() or "docker compose falhou")
        return result

    existing = _existing_containers()
    for spec in SERVICES:
        if spec.name in existing:
            proc = _run(["docker", "start", spec.name])
            action = "start"
        else:
            proc = _run(docker_run_cmd(spec))
            action = "run"
        if proc.returncode == 0:
            result.messages.append(f"{spec.name}: docker {action} ok")
        else:
            result.ok = False
            result.messages.append(
                f"{spec.name}: falha no docker {action} — {proc.stderr.strip()}"
            )
    return result


def stack_down() -> StackResult:
    """Para os containers da infra local (sem apagar volumes)."""
    result = StackResult(ok=True)

    if not _docker_available():
        result.ok = False
        result.messages.append("Docker não encontrado ou daemon parado.")
        return result

    compose = compose_file()
    if compose is not None:
        proc = _run(["docker", "compose", "-f", str(compose), "down"])
        if proc.returncode == 0:
            result.messages.append(f"docker compose down ({compose})")
        else:
            result.ok = False
            result.messages.append(proc.stderr.strip() or "docker compose falhou")
        return result

    existing = _existing_containers()
    for spec in SERVICES:
        if spec.name not in existing:
            result.messages.append(f"{spec.name}: não existe — nada a fazer")
            continue
        proc = _run(["docker", "stop", spec.name])
        if proc.returncode == 0:
            result.messages.append(f"{spec.name}: parado")
        else:
            result.ok = False
            result.messages.append(
                f"{spec.name}: falha ao parar — {proc.stderr.strip()}"
            )
    return result


def connection_urls() -> dict[str, str]:
    """URLs de conexão da stack local — as mesmas do defaults.env."""
    return {
        "POSTGRES_DSN": DEFAULT_POSTGRES_DSN,
        "REDIS_URL": DEFAULT_REDIS_URL,
        "QDRANT_URL": DEFAULT_QDRANT_URL,
        "QDRANT_API_KEY": DEFAULT_QDRANT_API_KEY,
    }
