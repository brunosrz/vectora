"""RewindScreen — confirmação de rewind na TUI Vectora.

Exibe os checkpoints disponíveis para o thread atual e deixa o usuário
confirmar antes de retroceder. Depende da API
``POST /threads/{id}/rewind`` (A.2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, OptionList, Static
from textual.widgets.option_list import Option

from backend.ui.i18n import t


class RewindScreen(ModalScreen[str | None]):
    """Modal de confirmação de rewind — lista checkpoints e confirma."""

    BINDINGS = [
        Binding("escape", "dismiss_none", "Cancelar", show=True),
    ]

    def __init__(
        self,
        thread_id: str,
        *,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._tid: str = thread_id

    def compose(self) -> ComposeResult:
        with Vertical(id="rewind-modal"):
            yield Static(f"[bold]{t('tui.rewind.title')}[/bold]", id="rw-title")
            yield Label(t("tui.rewind.description"), id="rw-desc")
            yield OptionList(id="rw-checkpoints")
            with Horizontal(id="rw-footer"):
                yield Button(
                    t("tui.rewind.confirm"), id="rw-confirm", variant="warning"
                )
                yield Button(t("tui.rewind.cancel"), id="rw-cancel")

    async def on_mount(self) -> None:
        await self._load_checkpoints()

    async def _load_checkpoints(self) -> None:
        ol = self.query_one("#rw-checkpoints", OptionList)
        checkpoints = await _fetch_checkpoints(self._tid)
        if not checkpoints:
            ol.add_option(Option(t("tui.rewind.no_checkpoints"), id="none"))
        else:
            for cp in checkpoints:
                cp_id = str(cp.get("checkpoint_id", ""))
                created = str(cp.get("created_at", ""))[:19]
                label = f"{created}  [{cp_id[:8]}]"
                ol.add_option(Option(label, id=cp_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rw-confirm":
            ol = self.query_one("#rw-checkpoints", OptionList)
            highlighted = ol.highlighted
            if highlighted is not None:
                option = ol.get_option_at_index(highlighted)
                cp_id = str(option.id)
                if cp_id != "none":
                    self.dismiss(cp_id)
                    return
        self.dismiss(None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_checkpoints(thread_id: str) -> list[dict[str, Any]]:
    """Lê checkpoints do DB local diretamente (sem HTTP)."""
    try:
        import aiosqlite

        db_path = Path.home() / ".vectora" / "checkpoints.db"
        if not db_path.exists():
            return []
        async with aiosqlite.connect(str(db_path)) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT checkpoint_id, strategy, created_at "
                "FROM vectora_checkpoint_artifacts "
                "WHERE thread_id = ? ORDER BY created_at DESC LIMIT 10",
                (thread_id,),
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
