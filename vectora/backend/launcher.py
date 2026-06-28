"""Launcher Vectora — entry-point do binário Nuitka.

Valida a licença antes de importar FastAPI/LangGraph/vector stores
(que custam segundos de boot), exporta ``VECTORA_TIER`` no environ
e delega para ``src.main:run``.

``VECTORA_LICENSE_BYPASS=1`` pula o gate inteiro — uso interno
(dev, CI). Nunca documentar em produção.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("backend.launcher")


def _print_error(message: str) -> None:
    """Imprime erro em stderr com formato consistente."""
    sys.stderr.write(f"\n[Vectora] {message}\n\n")
    sys.stderr.flush()


def main() -> int:
    """Entry-point do binário Vectora compilado."""
    # Lazy import: licença reprovada → exit em <1s, sem custo de carga
    # de FastAPI/LangGraph/vector stores.
    from backend.services.license import LicenseError, validate_license_sync

    try:
        info = validate_license_sync()
    except LicenseError as exc:
        _print_error(str(exc))
        return 2
    except Exception as exc:
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

    if info.days_remaining <= 7 and info.status == "trial":
        sys.stderr.write(
            f"\n[Vectora] Trial expira em {info.days_remaining} dia(s). "
            "Renove em https://vectora.company/pricing.\n\n"
        )

    from backend.main import run as cli_run

    cli_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
