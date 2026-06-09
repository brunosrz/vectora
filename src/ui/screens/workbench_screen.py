"""WorkbenchScreen — painel lateral com 4 abas na TUI Vectora.

Abas:
  Terminal  — saída do PTY em RichLog
  Files     — árvore de arquivos do workspace ativo (Tree)
  Diff      — status git resumido (DataTable)
  Plan      — artefatos do agente (Static)

Atalho ``Ctrl+` `` abre/fecha o painel do ChatScreen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from src.services.workspace import workspace_registry
from src.ui.i18n import t


class WorkbenchScreen(ModalScreen[None]):
    """Painel de workbench (Terminal / Files / Diff / Plan) em modal."""

    BINDINGS = [
        Binding("escape", "dismiss", "Fechar", show=True),
        Binding("ctrl+grave_accent", "dismiss", "Fechar", show=False),
    ]

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="workbench-modal"):
            yield Static(f"[bold]{t('tui.workbench.title')}[/bold]", id="wb-title")
            with TabbedContent(
                t("tui.workbench.tab_terminal"),
                t("tui.workbench.tab_files"),
                t("tui.workbench.tab_diff"),
                t("tui.workbench.tab_plan"),
                id="wb-tabs",
            ):
                with TabPane(t("tui.workbench.tab_terminal"), id="tab-terminal"):
                    yield RichLog(id="wb-terminal", highlight=True, markup=True)
                with TabPane(t("tui.workbench.tab_files"), id="tab-files"):
                    yield Tree(t("tui.workbench.files_root"), id="wb-files")
                with TabPane(t("tui.workbench.tab_diff"), id="tab-diff"):
                    yield DataTable(id="wb-diff")
                with TabPane(t("tui.workbench.tab_plan"), id="tab-plan"):
                    yield Static("", id="wb-plan")
            yield Label(t("tui.workbench.hint"), id="wb-hint")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def on_mount(self) -> None:
        self._populate_terminal()
        self._populate_files()
        self._populate_diff()
        self._populate_plan()

    # ------------------------------------------------------------------
    # Terminal — mostra últimas linhas do log da sessão
    # ------------------------------------------------------------------

    def _populate_terminal(self) -> None:
        log = self.query_one("#wb-terminal", RichLog)
        log_path = Path.home() / ".vectora" / "vectora.log"
        if log_path.exists():
            try:
                text = log_path.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()[-50:]  # últimas 50 linhas
                for line in lines:
                    log.write(line)
            except OSError:
                log.write(t("tui.workbench.terminal_unavailable"))
        else:
            log.write(t("tui.workbench.terminal_empty"))

    # ------------------------------------------------------------------
    # Files — árvore do workspace ativo (primeiro da lista)
    # ------------------------------------------------------------------

    def _populate_files(self) -> None:
        tree = self.query_one("#wb-files", Tree)
        workspaces = workspace_registry.list_all()
        if not workspaces:
            tree.root.add_leaf(t("tui.workbench.files_no_workspace"))
            tree.root.expand()
            return

        ws = workspaces[0]
        root_path = Path(ws.cwd)
        tree.root.label = root_path.name or str(root_path)
        _add_directory(tree.root, root_path, depth=0, max_depth=2)
        tree.root.expand()

    # ------------------------------------------------------------------
    # Diff — git status resumido
    # ------------------------------------------------------------------

    def _populate_diff(self) -> None:
        table = self.query_one("#wb-diff", DataTable)
        table.add_columns(
            t("tui.workbench.diff_col_status"),
            t("tui.workbench.diff_col_file"),
        )
        workspaces = workspace_registry.list_all()
        if not workspaces:
            return
        ws = workspaces[0]
        try:
            import git as gitpkg  # type: ignore[import-untyped]

            repo = gitpkg.Repo(ws.cwd, search_parent_directories=True)
            for item in repo.index.diff(None):  # unstaged
                table.add_row("M", item.a_path)
            for item in repo.index.diff("HEAD"):  # staged
                table.add_row("S", item.a_path)
            for path in repo.untracked_files:
                table.add_row("?", path)
        except Exception:  # noqa: BLE001
            table.add_row("-", t("tui.workbench.diff_unavailable"))

    # ------------------------------------------------------------------
    # Plan — artefatos listados por tipo
    # ------------------------------------------------------------------

    def _populate_plan(self) -> None:
        plan_widget = self.query_one("#wb-plan", Static)
        workspaces = workspace_registry.list_all()
        if not workspaces:
            plan_widget.update(t("tui.workbench.plan_no_workspace"))
            return
        ws = workspaces[0]
        artifacts_path = Path(ws.cwd) / ".vectora" / "artifacts"
        if not artifacts_path.exists():
            plan_widget.update(t("tui.workbench.plan_empty"))
            return
        try:
            entries = sorted(artifacts_path.iterdir())
            if not entries:
                plan_widget.update(t("tui.workbench.plan_empty"))
                return
            lines = [f"[bold]{t('tui.workbench.plan_title')}[/bold]"]
            for entry in entries[:20]:
                lines.append(f"  • {entry.name}")
            plan_widget.update("\n".join(lines))
        except OSError:
            plan_widget.update(t("tui.workbench.plan_unavailable"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKIP_DIRS = frozenset(
    {".git", "node_modules", "__pycache__", ".venv", "venv", ".vectora"}
)


def _add_directory(
    node: Any,
    path: Path,
    depth: int,
    max_depth: int,
) -> None:
    """Adiciona entradas de `path` ao nó da árvore recursivamente."""
    if depth >= max_depth:
        return
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return
    for entry in entries:
        if entry.name.startswith(".") and entry.name not in {".env", ".envrc"}:
            continue
        if entry.is_dir():
            if entry.name in _SKIP_DIRS:
                continue
            child = node.add(f"[blue]{entry.name}/[/blue]")
            _add_directory(child, entry, depth + 1, max_depth)
        else:
            node.add_leaf(entry.name)
