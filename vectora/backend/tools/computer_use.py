"""Controle de mouse/teclado da tela do desktop — a tool de maior risco.

Diferente de toda outra tool do produto, `computer_use` age fora do sandbox
de arquivo/terminal: um clique errado é irreversível (não existe
`git checkout` pra desfazer ter clicado no botão errado). Por isso duas
proteções que nenhuma outra tool tem:

- **Opt-in explícito por workspace** (`[computer_use] enabled = true` em
  `vectora.toml`) — sem a seção, a tool recusa antes de tocar em qualquer
  coisa. Nunca liga silenciosamente.
- **Aprovação humana sempre**, mesmo em `permission_mode="bypass"` — ver
  `_mode_should_interrupt` em `backend/services/middleware.py`, que abre
  uma exceção só pra esta tool.

A biblioteca de automação é ``pyautogui-next`` (fork mantido do PyAutoGUI
original, mesmo import ``pyautogui`` — o original está sem release desde
2022).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

logger = logging.getLogger(__name__)

_ACOES_VALIDAS = frozenset({"screenshot", "click", "type_text"})


def _computer_use_enabled_for_cwd(cwd: str) -> bool:
    """Lê `[computer_use]` de `vectora.toml` no `cwd` dado.

    Ausência de arquivo/seção é `False` — `load_workspace_config` já
    degrada pra `None`/defaults em qualquer erro de I/O ou parse."""
    from backend.workspace.workspace_config import load_workspace_config

    config = load_workspace_config(cwd)
    return bool(config and config.computer_use.enabled)


def _computer_use_enabled(workspace_id: str) -> bool:
    """Resolve o opt-in a partir do `workspace_id` do config da tool.

    Fail-closed: workspace desconhecida ou qualquer erro ao resolver o
    `cwd` volta `False` — nunca assume habilitado por omissão."""
    if not workspace_id:
        return False
    try:
        from backend.workspace.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        cwd = getattr(ws, "cwd", None)
        return bool(cwd) and _computer_use_enabled_for_cwd(str(cwd))
    except Exception:
        logger.debug(
            "computer_use: falha ao checar opt-in da workspace %s", workspace_id
        )
        return False


def _media_dir(session_id: str) -> Path:
    return (
        Path.home() / ".vectora" / "artifacts" / (session_id or "sem-sessao") / "media"
    )


def _take_screenshot() -> bytes:
    import io

    import pyautogui

    buffer = io.BytesIO()
    pyautogui.screenshot().save(buffer, format="PNG")
    return buffer.getvalue()


def _click(x: int, y: int) -> None:
    import pyautogui

    pyautogui.click(x=x, y=y)


def _type_text(text: str) -> None:
    import pyautogui

    pyautogui.typewrite(text)


def _session_id(config: RunnableConfig | None) -> str:
    return (
        str((config.get("configurable") or {}).get("thread_id", "")) if config else ""
    )


def _workspace_id(config: RunnableConfig | None) -> str:
    return (
        str((config.get("configurable") or {}).get("workspace_id", ""))
        if config
        else ""
    )


@tool(
    extras={
        "render_hint": "json",
        "category": "computer_use",
        "destructive": True,
        "icon": "monitor",
    }
)
def computer_use(
    action: str,
    x: int | None = None,
    y: int | None = None,
    text: str = "",
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Controla mouse/teclado da tela do desktop — `screenshot`, `click`, `type_text`.

    Ação física na máquina do usuário, fora do sandbox de arquivo/terminal.
    Só existe quando o workspace tem `[computer_use] enabled = true` em
    `vectora.toml`, e sempre pede aprovação humana antes de executar,
    mesmo em modo `bypass`.

    Args:
        action: `screenshot` (captura a tela), `click` (requer `x`/`y`) ou
            `type_text` (requer `text`).
        x: Coordenada X do clique, obrigatória para `click`.
        y: Coordenada Y do clique, obrigatória para `click`.
        text: Texto a digitar, obrigatório para `type_text`.

    Returns:
        JSON com o resultado da ação, ou com `error`.
    """
    workspace_id = _workspace_id(config)
    try:
        if not _computer_use_enabled(workspace_id):
            return json.dumps(
                {
                    "error": (
                        "computer_use está desligada neste workspace — "
                        "adicione `[computer_use]\\nenabled = true` ao "
                        "vectora.toml pra habilitar"
                    )
                },
                ensure_ascii=False,
            )

        if action not in _ACOES_VALIDAS:
            return json.dumps(
                {"error": f"ação desconhecida: {action!r}"}, ensure_ascii=False
            )

        if action == "screenshot":
            data = _take_screenshot()
            directory = _media_dir(_session_id(config))
            directory.mkdir(parents=True, exist_ok=True)
            path = (
                directory / f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.png"
            )
            path.write_bytes(data)
            return json.dumps(
                {"action": "screenshot", "path": str(path)}, ensure_ascii=False
            )

        if action == "click":
            if x is None or y is None:
                return json.dumps({"error": "click exige x e y"}, ensure_ascii=False)
            _click(x, y)
            return json.dumps({"action": "click", "x": x, "y": y}, ensure_ascii=False)

        if not text:
            return json.dumps(
                {"error": "type_text exige texto não vazio"}, ensure_ascii=False
            )
        _type_text(text)
        return json.dumps({"action": "type_text"}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("computer_use: falha", extra={"action": action})
        return json.dumps(
            {"error": f"falha em computer_use: {exc}"}, ensure_ascii=False
        )


COMPUTER_USE_TOOLS: list[Any] = [computer_use]

__all__ = ["COMPUTER_USE_TOOLS", "computer_use"]
