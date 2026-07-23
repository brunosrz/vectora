"""Tests for src/nodes/tools.py"""

from __future__ import annotations

from backend.nodes.tools import ALL_TOOLS, FS_TOOLS, MEMORY_TOOLS, SEARCH_TOOLS


def test_fs_tools_not_empty():
    assert len(FS_TOOLS) > 0


def test_memory_tools_not_empty():
    assert len(MEMORY_TOOLS) > 0


def test_search_tools_not_empty():
    assert len(SEARCH_TOOLS) > 0


def test_all_tools_is_union():
    assert len(ALL_TOOLS) >= len(SEARCH_TOOLS)
    assert len(ALL_TOOLS) >= len(FS_TOOLS)
    assert len(ALL_TOOLS) >= len(MEMORY_TOOLS)


def test_tools_have_names():
    for tool in ALL_TOOLS:
        assert hasattr(tool, "name")
        assert isinstance(tool.name, str)
        assert len(tool.name) > 0


def test_search_tools_include_web_search():
    names = [t.name for t in SEARCH_TOOLS]
    assert "web_search" in names


def test_fs_tools_include_file_read():
    names = [t.name for t in FS_TOOLS]
    assert "file_read" in names


def test_memory_tools_include_save_memory():
    names = [t.name for t in MEMORY_TOOLS]
    assert "save_memory" in names


def test_manage_retriever_registered():
    # Bloco A5.3 — a tool de gestão do RAG deve estar disponível aos agentes.
    names = [t.name for t in ALL_TOOLS]
    assert "manage_retriever" in names


def test_workspace_tools_registered():
    # Bloco B6 — ferramentas de workspace expostas aos agentes.
    names = [t.name for t in ALL_TOOLS]
    assert "workspace_describe" in names
    assert "workspace_list" in names
    assert "bucket_summary" in names


def test_search_memory_registered():
    # C4 — busca semântica em memórias deve estar disponível aos agentes.
    names = [t.name for t in ALL_TOOLS]
    assert "search_memory" in names


def test_all_tools_count():
    # Guarda contra perda acidental de registro de ferramentas — atualize ao
    # adicionar/remover tool em backend/nodes/tools.py.
    assert len(ALL_TOOLS) == 106


def test_background_task_tools_registered():
    # Sprint 3.3/3.4 — o orquestrador lista/consulta E intervém em tasks/runs.
    names = {t.name for t in ALL_TOOLS}
    for expected in (
        "create_background_task",
        "list_background_tasks",
        "get_task_status",
        "get_task_result",
        "approve_task_action",
    ):
        assert expected in names, f"Tool de background ausente: {expected}"


def test_browser_tools_registered():
    # A2 — automação de browser sobre o preview do workspace (Playwright).
    names = {t.name for t in ALL_TOOLS}
    for expected in (
        "browser_screenshot",
        "browser_click",
        "browser_scroll",
        "browser_fill",
        "browser_read_dom",
    ):
        assert expected in names, f"Browser tool ausente: {expected}"


def test_native_tools_registered():
    # Utilitários nativos (backend/tools/native/) existem e têm testes
    # próprios, mas até aqui nunca chegavam ao agente real — ALL_TOOLS não
    # os importava e o único consumidor de backend/tools/__init__.py::TOOLS
    # (mcp/server.py) também não. O agente ficava sem time_now/hash_text/etc.
    names = {t.name for t in ALL_TOOLS}
    for expected in (
        "time_now",
        "time_parse",
        "hash_text",
        "base64_encode",
        "base64_decode",
        "regex_test",
        "json_query",
        "jwt_decode",
        "http_request",
    ):
        assert expected in names, f"Native tool ausente: {expected}"


def test_native_tools_registered_in_chat_mode():
    from backend.nodes.tools import CHAT_TOOLS

    names = {t.name for t in CHAT_TOOLS}
    assert "time_now" in names
    assert "hash_text" in names


def test_graph_tools_registered():
    # Context graph tools (GF-3) devem estar disponíveis aos agentes.
    names = [t.name for t in ALL_TOOLS]
    for expected in (
        "build_knowledge_graph",
        "graph_query",
        "graph_explain",
        "graph_path",
    ):
        assert expected in names, f"Tool ausente: {expected}"
    # Erro: tools que não existem não devem estar presentes
    assert "context_graph_build" not in names
