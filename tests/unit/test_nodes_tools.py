"""Tests for vectora/nodes/tools.py"""

from __future__ import annotations

from vectora.nodes.tools import ALL_TOOLS, FS_TOOLS, MEMORY_TOOLS, SEARCH_TOOLS


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
    # 37 tools após o Bloco G3 (20 anteriores + 17 git/gh tools).
    # Guarda contra perda acidental de registro de ferramentas.
    assert len(ALL_TOOLS) == 37
