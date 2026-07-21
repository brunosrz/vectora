"""Parser da política de sandbox (`vectora.toml`, seção `[sandbox]`).

Modelo de ameaça: supply-chain attack via `terminal`/`npm install`
malicioso, exfiltração de credenciais (`~/.ssh`, `~/.aws`, vault local do
Vectora), modificação destrutiva fora do workspace confiado. Referência de
design: `akitaonrails/ai-jail` (Rust/bubblewrap) — reimplementação própria,
nunca forkada, com nomes de campo ao estilo Vectora.
"""

from __future__ import annotations

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
        )
    except Exception:
        logger.warning(
            "sandbox: campo inválido em [sandbox] de %s — fail-closed",
            vectora_toml_path,
        )
        return LOCKED_DOWN_POLICY
