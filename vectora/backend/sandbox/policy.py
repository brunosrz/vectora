"""Parser da política de sandbox (`vectora.toml`, seção `[sandbox]`).

Modelo de ameaça: supply-chain attack via `terminal`/`npm install`
malicioso, exfiltração de credenciais (`~/.ssh`, `~/.aws`, vault local do
Vectora), modificação destrutiva fora do workspace confiado. Referência de
design: `akitaonrails/ai-jail` (Rust/bubblewrap) — reimplementação própria,
nunca forkada, com nomes de campo ao estilo Vectora.
"""

from __future__ import annotations

import asyncio
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_MASK = (".env", "**/*.pem", "**/.ssh/**", "**/.aws/**")


@dataclass(frozen=True)
class SandboxPolicy:
    """Política resolvida — sempre um valor concreto, nunca `None`; ausência
    de `vectora.toml`/seção `[sandbox]` já vira `enabled=False` aqui."""

    enabled: bool = False
    backend: str = "local"
    rw_paths: tuple[str, ...] = ()
    ro_paths: tuple[str, ...] = ()
    mask: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_MASK)
    no_gpu: bool = True
    lockdown: bool = False
    docker_image: str | None = None
    remote_host: str | None = None
    ssh_key_id: str | None = None


DISABLED_POLICY = SandboxPolicy(enabled=False)

# Política mais restritiva possível — usada quando o parse falha (fail-closed:
# preferimos negar execução a rodar sem proteção por um TOML corrompido).
LOCKED_DOWN_POLICY = SandboxPolicy(
    enabled=True, backend="local", lockdown=True, rw_paths=()
)


def parse_policy(vectora_toml_path: Path) -> SandboxPolicy:
    """Lê `[sandbox]` de `vectora.toml`.

    Ausência de arquivo ou de seção `[sandbox]`: sandbox desabilitado
    (comportamento atual do produto é preservado, sem regressão — isto não
    é "fail closed", é "não opt-in"). TOML malformado ou campo com tipo
    errado, uma vez que `[sandbox]` EXISTE: fail-closed — devolve a
    política mais restritiva em vez de propagar exceção ou (pior) ignorar
    o erro e desabilitar a proteção silenciosamente.
    """
    if not vectora_toml_path.is_file():
        return DISABLED_POLICY
    try:
        raw = tomllib.loads(vectora_toml_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning(
            "sandbox: %s malformado — fail-closed (negando execução)",
            vectora_toml_path,
        )
        return LOCKED_DOWN_POLICY

    section = raw.get("sandbox")
    if not isinstance(section, dict):
        return DISABLED_POLICY

    try:
        return SandboxPolicy(
            enabled=bool(section.get("enabled", True)),
            backend=str(section.get("backend", "local")),
            rw_paths=tuple(str(p) for p in section.get("rw_paths", [])),
            ro_paths=tuple(str(p) for p in section.get("ro_paths", [])),
            mask=tuple(str(p) for p in section.get("mask", _DEFAULT_MASK)),
            no_gpu=bool(section.get("no_gpu", True)),
            lockdown=bool(section.get("lockdown", False)),
            docker_image=(
                str(section["docker_image"]) if "docker_image" in section else None
            ),
            remote_host=(
                str(section["remote_host"]) if "remote_host" in section else None
            ),
            ssh_key_id=(
                str(section["ssh_key_id"]) if "ssh_key_id" in section else None
            ),
        )
    except Exception:
        logger.warning(
            "sandbox: campo inválido em [sandbox] de %s — fail-closed",
            vectora_toml_path,
        )
        return LOCKED_DOWN_POLICY


class _Unset:
    """Sentinel — distingue "ainda não checado" de "checado, sem distro" (None)."""


_UNSET = _Unset()
_wsl2_distro_cache: str | None | _Unset = _UNSET


async def detect_wsl2() -> str | None:
    """Detecta uma distro WSL2 elegível (kernel Linux real, WSL versão 2 —
    não WSL1) via `wsl.exe -l -v`. É o único caminho real de sandbox no
    Windows: bwrap não roda nativo (sem namespace/mount API equivalente),
    e WSL2 é exatamente o caminho que o `ai-jail` original usa nesse SO —
    Docker não entra nessa equação.

    Cacheado por processo — o ambiente (WSL instalado ou não) não muda em
    runtime. Retorna `None` (não levanta) se `wsl.exe` não existir, falhar,
    ou nenhuma distro estiver em WSL2.
    """
    global _wsl2_distro_cache
    if not isinstance(_wsl2_distro_cache, _Unset):
        return _wsl2_distro_cache

    distro = await _detect_wsl2_uncached()
    _wsl2_distro_cache = distro
    return distro


async def _detect_wsl2_uncached() -> str | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "wsl.exe",
            "-l",
            "-v",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, _ = await asyncio.wait_for(proc.communicate(), timeout=10.0)
    except (FileNotFoundError, TimeoutError, OSError):
        return None
    if proc.returncode != 0:
        return None

    # `wsl.exe -l -v` imprime UTF-16LE no Windows — decodificar como UTF-8
    # produz lixo intercalado com bytes nulos.
    try:
        text = stdout_b.decode("utf-16-le")
    except UnicodeDecodeError:
        text = stdout_b.decode("utf-8", errors="replace")

    default_distro: str | None = None
    fallback_distro: str | None = None
    for line in text.splitlines():
        stripped = line.strip().lstrip("*").strip()
        if not stripped or stripped.upper().startswith("NAME"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        name, version = parts[0], parts[-1]
        if version != "2":
            continue
        if line.strip().startswith("*"):
            default_distro = name
        elif fallback_distro is None:
            fallback_distro = name
    return default_distro or fallback_distro
