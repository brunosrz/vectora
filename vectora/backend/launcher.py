"""Launcher Vectora — entry-point do binário Nuitka.

Valida a licença antes de importar FastAPI/LangGraph/vector stores
(que custam segundos de boot), exporta ``VECTORA_TIER`` no environ
e delega para ``src.main:run``.

``VECTORA_LICENSE_BYPASS=1`` pula o gate inteiro — uso interno
(dev, CI). Nunca documentar em produção.
"""

# ─── Opções de build do Nuitka (FONTE DE VERDADE) ──────────────────────────────
# O Nuitka LÊ estas diretivas ao compilar este arquivo (`nuitka backend/launcher.py`).
# `SConstruct` (build-nuitka) e o CI (runner.yml) só precisam chamar o nuitka — não
# repassam mais estas flags. Paths usam {MAIN_DIRECTORY} (= dir deste script,
# `backend`) ancorado em `..` para apontar à raiz do repo, independente do CWD.
#
# `frontend/dist/` (SPA Vite) é embutido como `chat_static/`; em runtime o FastAPI
# (backend/api/server.py::_chat_static_root) localiza via __compiled__.containing_dir
# / NUITKA_ONEFILE_PARENT e serve por StaticFiles. Rode `pnpm --dir frontend build` antes.
#
# Os --nofollow-import-to podam ferramentas de DEV que entram no grafo de imports
# (mypy/pytest/ruff/ty/…): nada disso roda em produção e compilá-las inflava o
# build em milhares de arquivos C. `--jobs` é o único knob dinâmico e fica no CLI.
#
# `--msvc=latest` fixa o compilador no MSVC do VS Build Tools. Sem isso o Nuitka
# escolhe o `zig` (presente como dep no venv) e a compilação de módulos grandes
# (google.genai.types, qdrant_client.http.models) passa de minutos para horas.
# Requer VS Build Tools com workload VCTools + Windows SDK instalados.
#
# nuitka-project: --mode=onefile
# nuitka-project: --msvc=latest
# nuitka-project: --output-filename=vectora
# nuitka-project: --output-dir={MAIN_DIRECTORY}/../dist-nuitka
# nuitka-project: --include-data-dir={MAIN_DIRECTORY}/../frontend/dist=chat_static
# nuitka-project: --include-data-dir={MAIN_DIRECTORY}/assets=backend/assets
# nuitka-project: --nofollow-import-to=mypy
# nuitka-project: --nofollow-import-to=pytest
# nuitka-project: --nofollow-import-to=_pytest
# nuitka-project: --nofollow-import-to=coverage
# nuitka-project: --nofollow-import-to=bandit
# nuitka-project: --nofollow-import-to=ty
# nuitka-project: --nofollow-import-to=ruff
# nuitka-project: --nofollow-import-to=pyright
# nuitka-project: --nofollow-import-to=IPython
# nuitka-project: --nofollow-import-to=black
# nuitka-project: --nofollow-import-to=isort
# nuitka-project: --include-module=backend.services.ipc_pipe_win
#
# langchain_core / langgraph resolvem submódulos por lazy import (`__getattr__`
# → `_import_utils.import_attr`), invisíveis à análise estática do Nuitka. Sem
# embarcar os pacotes inteiros o binário falha em runtime com ImportError (ex.:
# `langchain_core.embeddings.embeddings` puxado por `langgraph.store.base`).
# nuitka-project: --include-package=langchain_core
# nuitka-project: --include-package=langgraph
# nuitka-project: --include-package=langchain
# nuitka-project: --include-package=deepagents

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
