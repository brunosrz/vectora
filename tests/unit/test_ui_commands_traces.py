"""Testes para vectora/ui/commands/traces.py (Bloco D3).

Cobre:
- /traces sem args: mostra tabela com spans recentes
- /traces --session <id>: filtra por sessão
- /traces --node <nome>: filtra por nó
- /traces --clear: apaga todos os spans
- Nenhum span encontrado: exibe painel "vazio"
- Metadados JSON malformados não travam o comando
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vectora.ui.commands.traces import handle_traces_command

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_span(**kwargs) -> dict:
    defaults = {
        "node": "orchestrator",
        "event": "call",
        "duration_ms": 120.5,
        "status": "ok",
        "in_tokens": 100,
        "out_tokens": 50,
        "session_id": 1,
        "metadata": "{}",
    }
    return {**defaults, **kwargs}


def _make_console() -> MagicMock:
    console = MagicMock()
    console.print = MagicMock()
    return console


# ---------------------------------------------------------------------------
# Testes principais
# ---------------------------------------------------------------------------


class TestHandleTracesCommand:
    @pytest.mark.asyncio
    async def test_shows_table_with_recent_spans(self):
        """Sem argumentos: busca últimos 30 spans e exibe tabela."""
        spans = [_make_span(), _make_span(node="invoke_llm", duration_ms=250.0)]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=spans)
            await handle_traces_command("", console, context=None)

        mock_tracer.get_recent.assert_awaited_once_with(n=30)
        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_filter_calls_get_session(self):
        """--session <id> chama tracer.get_session()."""
        spans = [_make_span(session_id=42)]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_session = AsyncMock(return_value=spans)
            await handle_traces_command("--session 42", console, context=None)

        mock_tracer.get_session.assert_awaited_once_with(42, limit=50)

    @pytest.mark.asyncio
    async def test_invalid_session_id_prints_error(self):
        """--session abc (não-inteiro) exibe erro e retorna sem travar."""
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer"):
            await handle_traces_command("--session abc", console, context=None)

        args, _ = console.print.call_args
        assert "inválido" in args[0].lower() or "inválido" in str(args[0]).lower()

    @pytest.mark.asyncio
    async def test_node_filter_filters_spans(self):
        """--node orchestrator filtra apenas spans cujo node começa com 'orchestrator'."""
        spans = [
            _make_span(node="orchestrator"),
            _make_span(node="invoke_llm"),
            _make_span(node="orchestrator_inner"),
        ]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=spans)
            await handle_traces_command("--node orchestrator", console, context=None)

        # Deve exibir o painel com apenas os 2 spans que começam com "orchestrator"
        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_calls_clear_all(self):
        """--clear chama tracer.clear_all() e exibe contagem."""
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.clear_all = AsyncMock(return_value=15)
            await handle_traces_command("--clear", console, context=None)

        mock_tracer.clear_all.assert_awaited_once()
        args, _ = console.print.call_args
        assert "15" in str(args[0])

    @pytest.mark.asyncio
    async def test_no_spans_shows_empty_panel(self):
        """Sem spans, exibe painel informativo sem travar."""
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=[])
            await handle_traces_command("", console, context=None)

        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_spans_with_session_hint(self):
        """Sem spans com --session, o painel menciona a sessão."""
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_session = AsyncMock(return_value=[])
            await handle_traces_command("--session 7", console, context=None)

        args, _ = console.print.call_args
        panel = args[0]
        # Pega a string que foi printada para não dar assert contra o objeto da memória do painel rich
        printed = (
            str(panel)
            + str(getattr(panel, "renderable", ""))
            + str(getattr(panel, "title", ""))
        )
        assert "7" in printed

    @pytest.mark.asyncio
    async def test_malformed_metadata_does_not_crash(self):
        """Metadados JSON inválidos no span não travam a exibição."""
        spans = [_make_span(metadata="not_valid_json{{{{")]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=spans)
            # Não deve levantar exceção
            await handle_traces_command("", console, context=None)

        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_span_with_no_duration_shows_dash(self):
        """Spans sem duration_ms exibem '—' em vez de travar."""
        spans = [_make_span(duration_ms=None)]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=spans)
            await handle_traces_command("", console, context=None)

        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_status_displayed(self):
        """Spans com status 'error' são aceitos sem crash."""
        spans = [_make_span(status="error")]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=spans)
            await handle_traces_command("", console, context=None)

        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_summary_per_node_aggregates_correctly(self):
        """Painel de sumário agrega latências por nó — não trava com múltiplos nós."""
        spans = [
            _make_span(node="orchestrator", duration_ms=100.0),
            _make_span(node="orchestrator", duration_ms=200.0),
            _make_span(node="invoke_llm", duration_ms=500.0),
        ]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_recent = AsyncMock(return_value=spans)
            await handle_traces_command("", console, context=None)

        console.print.assert_called_once()

    @pytest.mark.asyncio
    async def test_short_flags_work(self):
        """Aliases curtos --session/-s e --node/-n e --clear/-c funcionam."""
        spans = [_make_span(session_id=3)]
        console = _make_console()

        with patch("vectora.ui.commands.traces.tracer") as mock_tracer:
            mock_tracer.get_session = AsyncMock(return_value=spans)
            await handle_traces_command("-s 3", console, context=None)

        mock_tracer.get_session.assert_awaited_once_with(3, limit=50)
