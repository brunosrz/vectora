"""Launcher Vectora — entry-point único do binário comercial (T.12.1).

Quando o Vectora é distribuído como binário compilado por Nuitka (T.12.4),
``launcher.main`` é o entry-point — o shell Electron (T.12.5) faz spawn
deste binário e o usuário roda ``vectora`` diretamente.

Responsabilidades:

1. Validar ``VECTORA_TOKEN`` (Bloco T.12.7) antes de subir qualquer
   subprocesso. Sem licença válida, sai com mensagem explicativa.
2. Exportar ``VECTORA_TIER`` no ambiente para que a camada storage
   (V) e o cache distribuído (W) saibam quais backends podem subir.
3. Encadear no ``src.main:main`` — o CLI antigo continua sendo a
   máquina-de-estados que decide entre chat/mcp/headless/desktop.

**Modo dev**: ``VECTORA_LICENSE_BYPASS=1`` pula o gate (uso interno).
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("vectora.launcher")


def _print_error(message: str) -> None:
    """Imprime erro em stderr com formato consistente."""
    sys.stderr.write(f"\n[Vectora] {message}\n\n")
    sys.stderr.flush()


def main() -> int:
    """Entry-point do binário Vectora compilado."""
    # Lazy import para que o gate de licença execute antes de carregar
    # FastAPI, LangGraph, vector stores etc. — boot mais rápido em erro.
    from src.services.license import LicenseError, validate_license_sync

    try:
        info = validate_license_sync()
    except LicenseError as exc:
        _print_error(str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001
        _print_error(
            f"Falha inesperada validando licença: {exc}. "
            "Suporte: https://vectora.company/support."
        )
        return 3

    os.environ["VECTORA_TIER"] = info.tier
    logger.info(
        "license: tier=%s status=%s days_remaining=%d cached=%s",
        info.tier,
        info.status,
        info.days_remaining,
        info.cached,
    )

    if info.status == "expired":
        _print_error(
            "Licença Vectora expirada. Renove em https://vectora.company/pricing."
        )
        return 4

    # Aviso visível (não-bloqueante) quando faltam <=7 dias.
    if info.days_remaining <= 7 and info.status == "trial":
        sys.stderr.write(
            f"\n[Vectora] Trial expira em {info.days_remaining} dia(s). "
            "Renove em https://vectora.company/pricing.\n\n"
        )

    from src.main import run as cli_run

    cli_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
