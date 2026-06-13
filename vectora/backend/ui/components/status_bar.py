"""Texto da barra de status inferior (`#status-info`).

Monta `caminho · branch · modelo · modo` a partir de leitura pura de
ambiente/git, sem nenhuma dependência de widget. Função isolada (a parte
difícil de testar — `subprocess`/filesystem — fica concentrada aqui) para
testar a lógica sem precisar instanciar a App completa.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
from pathlib import Path

_SEP = "  ·  "


def _current_branch(cwd: Path) -> str:
    """Lê o branch git atual; string vazia fora de um repo ou sem git."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],  # noqa: S607  # nosec B603 B607
            capture_output=True,
            text=True,
            check=False,
            cwd=str(cwd),
            timeout=2,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _active_model() -> str:
    """Lê o modelo ativo das envs específicas de cada provider (1ª que existir)."""
    return (
        os.environ.get("GOOGLE_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or os.environ.get("ANTHROPIC_MODEL")
        or os.environ.get("COHERE_MODEL")
        or ""
    )


def build_status_text(permission_mode: str) -> str:
    """Monta `caminho · branch · modelo · modo` para `#status-info`.

    `permission_mode` vem de `VectoraChatApp._permission_mode` — único dado
    que a app precisa "emprestar"; todo o resto é lido daqui (cwd/git/env).
    """
    cwd = Path.cwd()
    home = Path.home()
    try:
        path_str = "~/" + str(cwd.relative_to(home))
    except ValueError:
        path_str = str(cwd)

    branch = _current_branch(cwd)
    model = _active_model()

    parts: list[str] = [path_str]
    if branch:
        parts.append(branch)
    if model:
        parts.append(model)
    parts.append(permission_mode)
    return _SEP.join(parts)
