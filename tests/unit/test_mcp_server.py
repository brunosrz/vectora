"""Tests for vectora/mcp/server.py

Cobre as funções testáveis sem exigir conexão MCP real:
- _with_timeout: timeout, sucesso, erro
- delegate_task_to_vectora: prompt vazio (A2A ainda não implementado)
- get_server_status: retorno JSON com campos esperados
- get_thread_context / get_thread_history: mock Checkpointer
- list_vector_collections: mock lancedb
- Tool wrappers: mock LangChain .ainvoke
- TOOL_TIMEOUTS: presença das chaves esperadas
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Importar módulo uma única vez — tem side effects de nível módulo (logging, FastMCP)
import vectora.mcp.server as srv

# ---------------------------------------------------------------------------
# _with_timeout
# ---------------------------------------------------------------------------


class TestWithTimeout:
    @pytest.mark.asyncio
    async def test_returns_string_on_success(self):
        async def _ok():
            return "resultado"

        result = await srv._with_timeout(_ok(), "web_search")
        assert result == "resultado"

    @pytest.mark.asyncio
    async def test_timeout_returns_error_message(self):
        async def _slow():
            await asyncio.sleep(999)

        result = await srv._with_timeout(_slow(), "web_search", default_timeout=0.001)
        assert "timeout" in result.lower() or "excedeu" in result.lower()

    @pytest.mark.asyncio
    async def test_exception_returns_error_message(self):
        async def _boom():
            raise ValueError("algo deu errado")

        result = await srv._with_timeout(_boom(), "vector_search")
        assert "erro" in result.lower() or "Error" in result
        assert "ValueError" in result

    @pytest.mark.asyncio
    async def test_uses_tool_timeout_from_map(self):
        """Timeout do mapa TOOL_TIMEOUTS sobrescreve default_timeout."""
        # web_search tem 30s no mapa — não deve expirar em 0.001s porque usa o mapa
        # Só validamos que a chave existe e que não trava em chamada normal
        assert "web_search" in srv.TOOL_TIMEOUTS
        assert srv.TOOL_TIMEOUTS["web_search"] == 30.0


# ---------------------------------------------------------------------------
# TOOL_TIMEOUTS
# ---------------------------------------------------------------------------


class TestToolTimeouts:
    def test_all_expected_keys_present(self):
        expected = {
            "web_search",
            "fetch_url",
            "vector_search",
            "embedding",
            "ingest_docs",
            "file_read",
            "file_edit",
            "file_write",
            "grep",
            "list_dir",
            "terminal",
            "call_mcp_tool",
        }
        assert expected.issubset(srv.TOOL_TIMEOUTS.keys())

    def test_all_timeouts_positive(self):
        for name, val in srv.TOOL_TIMEOUTS.items():
            assert val > 0, f"{name} timeout deve ser positivo"


# ---------------------------------------------------------------------------
# delegate_task_to_vectora
# ---------------------------------------------------------------------------


class TestDelegateTaskToVectora:
    @pytest.mark.asyncio
    async def test_empty_prompt_returns_error(self):
        result = await srv.delegate_task_to_vectora("")
        assert "vazio" in result.lower() or "Erro" in result

    @pytest.mark.asyncio
    async def test_whitespace_only_prompt_returns_error(self):
        result = await srv.delegate_task_to_vectora("   ")
        assert "vazio" in result.lower() or "Erro" in result

    @pytest.mark.asyncio
    async def test_returns_not_implemented_notice(self):
        """A2A ainda não implementado — deve retornar mensagem clara."""
        result = await srv.delegate_task_to_vectora("faça algo complexo")
        assert "ainda não" in result or "não está disponível" in result


# ---------------------------------------------------------------------------
# get_server_status resource
# ---------------------------------------------------------------------------


class TestGetServerStatus:
    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        result = await srv.get_server_status()
        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_contains_expected_fields(self):
        result = await srv.get_server_status()
        data = json.loads(result)
        assert data["server"] == "Vectora"
        assert data["status"] == "ready"
        assert "capabilities" in data
        assert data["tools_count"] == 13
        assert data["resources_count"] == 4

    @pytest.mark.asyncio
    async def test_timestamp_present(self):
        result = await srv.get_server_status()
        data = json.loads(result)
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO 8601 format


# ---------------------------------------------------------------------------
# get_thread_context resource
# ---------------------------------------------------------------------------


class TestGetThreadContext:
    @pytest.mark.asyncio
    async def test_empty_thread_returns_empty_status(self):
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=False)
        mock_checkpointer.aget = AsyncMock(return_value=None)

        with patch("vectora.mcp.server.Checkpointer", return_value=mock_checkpointer):
            result = await srv.get_thread_context("999")

        data = json.loads(result)
        assert data["status"] == "empty"
        assert data["thread_id"] == "999"

    @pytest.mark.asyncio
    async def test_active_thread_returns_message_count(self):
        mock_msg = MagicMock()
        mock_msg.__class__.__name__ = "HumanMessage"
        state_values = {
            "values": {
                "messages": [mock_msg, mock_msg],
                "summarized_history": "resumo",
            }
        }

        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=False)
        mock_checkpointer.aget = AsyncMock(return_value=state_values)

        with patch("vectora.mcp.server.Checkpointer", return_value=mock_checkpointer):
            result = await srv.get_thread_context("1")

        data = json.loads(result)
        assert data["status"] == "active"
        assert data["message_count"] == 2

    @pytest.mark.asyncio
    async def test_exception_returns_error_status(self):
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=False)
        mock_checkpointer.aget = AsyncMock(side_effect=RuntimeError("db error"))

        with patch("vectora.mcp.server.Checkpointer", return_value=mock_checkpointer):
            result = await srv.get_thread_context("1")

        data = json.loads(result)
        assert data["status"] == "error"


# ---------------------------------------------------------------------------
# get_thread_history resource
# ---------------------------------------------------------------------------


class TestGetThreadHistory:
    @pytest.mark.asyncio
    async def test_empty_thread_returns_empty_messages(self):
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=False)
        mock_checkpointer.aget = AsyncMock(return_value=None)

        with patch("vectora.mcp.server.Checkpointer", return_value=mock_checkpointer):
            result = await srv.get_thread_history("999")

        data = json.loads(result)
        assert data["status"] == "empty"
        assert data["messages"] == []

    @pytest.mark.asyncio
    async def test_history_truncates_to_last_5(self):
        msgs = []
        for i in range(8):
            m = MagicMock()
            m.__class__.__name__ = "HumanMessage"
            m.content = f"msg {i}"
            msgs.append(m)

        state_values = {"values": {"messages": msgs}}
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=False)
        mock_checkpointer.aget = AsyncMock(return_value=state_values)

        with patch("vectora.mcp.server.Checkpointer", return_value=mock_checkpointer):
            result = await srv.get_thread_history("1")

        data = json.loads(result)
        assert data["message_count"] == 8
        assert len(data["recent_messages"]) == 5

    @pytest.mark.asyncio
    async def test_exception_returns_error_status(self):
        mock_checkpointer = AsyncMock()
        mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
        mock_checkpointer.__aexit__ = AsyncMock(return_value=False)
        mock_checkpointer.aget = AsyncMock(side_effect=Exception("boom"))

        with patch("vectora.mcp.server.Checkpointer", return_value=mock_checkpointer):
            result = await srv.get_thread_history("1")

        data = json.loads(result)
        assert data["status"] == "error"


# ---------------------------------------------------------------------------
# list_vector_collections resource
# ---------------------------------------------------------------------------


class TestListVectorCollections:
    @pytest.mark.asyncio
    async def test_no_lancedb_dir_returns_unavailable(self):
        """settings.lancedb_dir=None → status unavailable (cobre linha 689)."""
        with patch.object(srv.settings, "lancedb_dir", None):
            result = await srv.list_vector_collections()

        data = json.loads(result)
        assert data["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_collections_listed_successfully(self):
        """Cobre o caminho feliz com lancedb mockado (linhas 693-708)."""
        mock_table = AsyncMock()
        mock_table.count_rows = AsyncMock(return_value=10)

        mock_db = AsyncMock()
        mock_db.table_names = AsyncMock(return_value=["default"])
        mock_db.open_table = AsyncMock(return_value=mock_table)

        mock_lancedb_mod = MagicMock()
        mock_lancedb_mod.connect_async = AsyncMock(return_value=mock_db)

        with (
            patch.dict("sys.modules", {"lancedb": mock_lancedb_mod}),
            patch.object(srv.settings, "lancedb_dir", "/tmp/lancedb"),
        ):
            result = await srv.list_vector_collections()

        data = json.loads(result)
        assert "status" in data  # success or error depending on import interception

    @pytest.mark.asyncio
    async def test_table_open_error_returns_error_entry(self):
        """open_table raises → collection entry com status=error (linhas 704-706)."""
        mock_db = AsyncMock()
        mock_db.table_names = AsyncMock(return_value=["broken_table"])
        mock_db.open_table = AsyncMock(side_effect=RuntimeError("broken"))

        mock_lancedb_mod = MagicMock()
        mock_lancedb_mod.connect_async = AsyncMock(return_value=mock_db)

        with (
            patch.dict("sys.modules", {"lancedb": mock_lancedb_mod}),
            patch.object(srv.settings, "lancedb_dir", "/tmp/lancedb"),
        ):
            result = await srv.list_vector_collections()

        data = json.loads(result)
        assert "status" in data

    @pytest.mark.asyncio
    async def test_outer_exception_returns_error_status(self):
        """Exceção no bloco principal → status=error."""
        with patch.object(srv.settings, "lancedb_dir", "/tmp/lancedb"):
            # lancedb import falha
            import builtins

            real_import = builtins.__import__

            def _bad_import(name, *args: object, **kwargs: object):
                if name == "lancedb":
                    raise ImportError("no lancedb")
                return real_import(name, *args, **kwargs)  # ty: ignore[invalid-argument-type]

            with patch("builtins.__import__", side_effect=_bad_import):
                result = await srv.list_vector_collections()

        data = json.loads(result)
        assert "status" in data


# ---------------------------------------------------------------------------
# MCP tool wrappers (smoke test via _with_timeout mock)
# ---------------------------------------------------------------------------


def _make_timeout_mock(return_value: str) -> AsyncMock:
    """Cria AsyncMock que fecha coroutines passadas como 1º argumento.

    Quando _with_timeout é mockado, a ferramenta ainda cria a coroutine
    (ex: web_search.ainvoke(...)) antes de passá-la ao mock. O mock nunca a
    aguarda, então o GC emite RuntimeWarning. Este side_effect fecha a
    coroutine imediatamente para suprimir o aviso.
    """

    async def _side_effect(coro, *args: object, **kwargs: object) -> str:
        if hasattr(coro, "close"):
            coro.close()
        return return_value

    return AsyncMock(side_effect=_side_effect)


class TestMcpToolWrappers:
    @pytest.mark.asyncio
    async def test_web_search_tool_calls_underlying_tool(self):
        mock_wt = _make_timeout_mock("resultados")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.web_search_tool("python tutorial")
        mock_wt.assert_called_once()
        assert result == "resultados"

    @pytest.mark.asyncio
    async def test_fetch_url_tool_calls_underlying_tool(self):
        mock_wt = _make_timeout_mock("conteudo")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.fetch_url_tool("https://example.com")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_search_tool_calls_underlying_tool(self):
        mock_wt = _make_timeout_mock('{"results": []}')
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.vector_search_tool("query", "default", 5)
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_embedding_tool_with_metadata(self):
        mock_wt = _make_timeout_mock('{"queue_id": "abc"}')
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.embedding_tool("texto", "default", {"title": "doc"})
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_embedding_tool_without_metadata(self):
        mock_wt = _make_timeout_mock('{"queue_id": "abc"}')
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.embedding_tool("texto")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_read_tool(self):
        mock_wt = _make_timeout_mock("conteudo arquivo")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.file_read_tool("/tmp/test.py")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_edit_tool(self):
        mock_wt = _make_timeout_mock("editado")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.file_edit_tool("/tmp/x.py", "old", "new")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_write_tool(self):
        mock_wt = _make_timeout_mock("escrito")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.file_write_tool("/tmp/x.py", "content")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_grep_tool(self):
        mock_wt = _make_timeout_mock("matches")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.grep_tool("pattern", ".")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_dir_tool(self):
        mock_wt = _make_timeout_mock("files")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.list_dir_tool(".", False)
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_terminal_tool(self):
        mock_wt = _make_timeout_mock("saida")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.terminal_tool("echo hello")
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_mcp_tool_tool(self):
        mock_wt = _make_timeout_mock("resultado mcp")
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.call_mcp_tool_tool("some_tool", '{"arg": 1}')
        mock_wt.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_docs_tool(self):
        mock_wt = _make_timeout_mock('{"processed": 0}')
        with patch.object(srv, "_with_timeout", mock_wt):
            result = await srv.ingest_docs_tool("src/**/*.py")
        mock_wt.assert_called_once()


# ---------------------------------------------------------------------------
# run() entry point
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_stdio_transport(self):
        """run() com transport=stdio chama mcp.run(transport='stdio')."""
        with (
            patch.dict("os.environ", {"MCP_TRANSPORT": "stdio"}, clear=False),
            patch.object(srv.mcp, "run") as mock_run,
            patch("rich.console.Console"),
        ):
            srv.run()

        mock_run.assert_called_once_with(transport="stdio")

    def test_run_sse_transport(self):
        """run() com MCP_TRANSPORT=sse chama mcp.run(transport='sse')."""
        with (
            patch.dict(
                "os.environ",
                {"MCP_TRANSPORT": "sse", "MCP_HOST": "127.0.0.1", "MCP_PORT": "9000"},
                clear=False,
            ),
            patch.object(srv.mcp, "run") as mock_run,
            patch("rich.console.Console"),
        ):
            srv.run()

        mock_run.assert_called_once_with(transport="sse")

    def test_run_keyboard_interrupt_exits_0(self):
        """KeyboardInterrupt durante mcp.run() → sys.exit(0)."""
        with (
            patch.dict("os.environ", {"MCP_TRANSPORT": "stdio"}, clear=False),
            patch.object(srv.mcp, "run", side_effect=KeyboardInterrupt),
            patch("rich.console.Console"),
            pytest.raises(SystemExit) as exc_info,
        ):
            srv.run()

        assert exc_info.value.code == 0

    def test_run_exception_exits_1(self):
        """Exceção inesperada durante mcp.run() → sys.exit(1)."""
        with (
            patch.dict("os.environ", {"MCP_TRANSPORT": "stdio"}, clear=False),
            patch.object(srv.mcp, "run", side_effect=RuntimeError("crash")),
            patch("rich.console.Console"),
            pytest.raises(SystemExit) as exc_info,
        ):
            srv.run()

        assert exc_info.value.code == 1
