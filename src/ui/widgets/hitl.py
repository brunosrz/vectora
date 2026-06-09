"""HITLModal — modal de aprovação de ferramentas da TUI Vectora.

Renderiza:
  - Nome da ferramenta + argumentos formatados
  - Raciocínio do agente (``reasoning``)
  - Arquivos afetados (``affected_paths``)
  - Preview de diff (``diff_preview``) quando disponível
  - 3 botões: Aprovar / Pular / Rejeitar

Retorna ``"approve"`` | ``"skip"`` | ``"reject"`` para o callback de HITL.
"""

from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from src.ui.i18n import t


class HITLModal(ModalScreen[str]):
    """Modal de aprovação — renderiza args, reasoning, paths e diff preview."""

    BINDINGS = [
        Binding("escape", "reject", "Rejeitar"),
    ]

    DEFAULT_CSS = """
    HITLModal {
        align: center middle;
    }
    #hitl-dialog {
        background: $surface;
        border: round $warning;
        padding: 1 2;
        width: 80;
        max-width: 90%;
        height: auto;
        max-height: 80%;
    }
    #hitl-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    #hitl-reasoning {
        color: $text-muted;
        margin-bottom: 1;
    }
    #hitl-paths {
        color: $text-muted;
        margin-bottom: 1;
    }
    #hitl-args {
        background: $panel;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
        max-height: 10;
        overflow-y: auto;
    }
    #hitl-diff {
        background: $panel;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
        max-height: 8;
        overflow-y: auto;
        color: $text;
    }
    #hitl-buttons {
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tool_name: str,
        args_json: str,
        interrupt_id: str,
        reasoning: str = "",
        affected_paths: list[str] | None = None,
        diff_preview: str = "",
    ) -> None:
        super().__init__()
        self._tool_name = tool_name
        self._args_json = args_json
        self._interrupt_id = interrupt_id
        self._reasoning = reasoning
        self._affected_paths = affected_paths or []
        self._diff_preview = diff_preview

    def compose(self) -> ComposeResult:
        try:
            pretty = json.dumps(
                json.loads(self._args_json), indent=2, ensure_ascii=False
            )
        except Exception:  # noqa: BLE001
            pretty = self._args_json
        pretty_truncated = pretty[:800] + ("…" if len(pretty) > 800 else "")

        with Center():
            with Vertical(id="hitl-dialog"):
                yield Label(
                    f"[bold yellow]⚡ {t('tui.hitl.approval_needed')}[/bold yellow]"
                    f" {self._tool_name}",
                    id="hitl-title",
                )
                if self._reasoning:
                    yield Static(
                        f"[dim]{self._reasoning[:200]}[/dim]",
                        id="hitl-reasoning",
                    )
                if self._affected_paths:
                    paths_str = "  ".join(self._affected_paths[:10])
                    yield Static(
                        f"[dim]📁 {paths_str}[/dim]",
                        id="hitl-paths",
                    )
                yield Static(pretty_truncated, id="hitl-args")
                if self._diff_preview:
                    diff_truncated = self._diff_preview[:600] + (
                        "…" if len(self._diff_preview) > 600 else ""
                    )
                    yield Static(diff_truncated, id="hitl-diff")
                with Horizontal(id="hitl-buttons"):
                    yield Button(t("tui.hitl.approve"), id="approve", variant="success")
                    yield Button(t("tui.hitl.skip"), id="skip", variant="warning")
                    yield Button(t("tui.hitl.reject"), id="reject", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "approve":
            self.dismiss("approve")
        elif bid == "skip":
            self.dismiss("skip")
        else:
            self.dismiss("reject")

    def action_reject(self) -> None:
        self.dismiss("reject")
