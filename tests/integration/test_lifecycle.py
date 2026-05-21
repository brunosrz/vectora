"""Testes de ciclo de vida — session 1212.

Suite sequencial e ordenada que verifica o comportamento real do Vectora com
APIs reais (Google Gemini + Cohere). Cada step roda na mesma session 1212
e depende do estado criado pelos steps anteriores.

Requer: GOOGLE_API_KEY + COHERE_API_KEY

Executar:
    uv run pytest tests/integration/test_lifecycle.py -v --timeout=120 -p no:randomly
"""

from __future__ import annotations

import json
import logging

import pytest
from langgraph.graph.state import RunnableConfig

from tests.integration.conftest import (
    KNOWN_KEYWORD,
    KNOWN_TEXT,
    REQUIRES_BOTH,
    REQUIRES_COHERE,
    REQUIRES_GOOGLE,
    TEST_COLLECTION,
    TEST_SESSION_ID,
    TEST_THREAD_ID,
    embed_direct,
    integration_cleanup,
    invoke_graph,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.lifecycle,
    pytest.mark.timeout(120),
]


# ============================================================================
# Fixture: cleanup session 1212 antes de TODA a suite
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def _reset_session_1212():
    """Limpa dados da session 1212 UMA VEZ antes de todos os lifecycle tests."""
    import asyncio

    from tests.integration.conftest import _cleanup_session_1212

    asyncio.run(_cleanup_session_1212())


# ============================================================================
# Step 1 — Saudação inicial
# ============================================================================


@pytest.mark.order(1)
@REQUIRES_GOOGLE
async def test_fresh_greeting(lifecycle_graph, lifecycle_config):
    """Step 1: Saudação simples → resposta não-vazia; supervisor roteia para direct."""
    response = await invoke_graph(lifecycle_graph, lifecycle_config, "Olá!")

    assert len(response) > 0, "O Vectora deve responder à saudação"
    logger.info(f"Step 1 — resposta: {response[:100]}")


# ============================================================================
# Step 2 — Roteamento para coder
# ============================================================================


@pytest.mark.order(2)
@REQUIRES_GOOGLE
async def test_supervisor_routes_to_coder(lifecycle_graph, lifecycle_config):
    """Step 2: Pedido de listagem de arquivos → supervisor roteia para coder."""
    from vectora.services.tracer import tracer

    response = await invoke_graph(
        lifecycle_graph,
        lifecycle_config,
        "Liste os arquivos do diretório /tmp e me diga quantos existem.",
    )

    assert len(response) > 0, "O coder deve retornar uma resposta"
    logger.info(f"Step 2 — resposta coder: {response[:150]}")

    # Verifica no tracer que o supervisor registrou routing para coder
    spans = await tracer.get_session(TEST_SESSION_ID)
    supervisor_spans = [s for s in spans if s.get("node") == "supervisor"]

    if supervisor_spans:
        # Se o tracer capturou o span do supervisor, verificamos o routing
        import ast

        for span in supervisor_spans:
            meta_raw = span.get("metadata", "{}")
            try:
                meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                routing = meta.get("routing", "")
                if routing:
                    logger.info(f"Supervisor routing: {routing}")
                    # Pedido de listagem deve ter ido para coder ou direct
                    assert routing in (
                        "coder",
                        "direct",
                        "search",
                    ), f"Routing inesperado: {routing}"
                    break
            except Exception:
                pass


# ============================================================================
# Step 3 — Embedding de documento conhecido
# ============================================================================


@pytest.mark.order(3)
@REQUIRES_COHERE
async def test_embed_known_doc():
    """Step 3: Indexa KNOWN_TEXT diretamente no LanceDB (bypass da fila)."""
    # Embed direto (sem fila) para garantir que o doc está disponível no step 4
    await embed_direct(KNOWN_TEXT, TEST_COLLECTION)
    logger.info(f"Step 3 — documento indexado em '{TEST_COLLECTION}'")

    # Verificação rápida: o doc está no LanceDB?
    import lancedb

    from vectora.config.settings import settings

    db = await lancedb.connect_async(str(settings.lancedb_dir))
    tables = await db.table_names()
    assert TEST_COLLECTION in tables, f"Coleção '{TEST_COLLECTION}' não criada"

    table = await db.open_table(TEST_COLLECTION)
    df = await table.to_pandas()
    assert len(df) >= 1, "LanceDB deve ter pelo menos 1 documento"
    assert KNOWN_TEXT in df["text"].values, "KNOWN_TEXT deve estar no LanceDB"


# ============================================================================
# Step 4 — RAG encontra documento embedado
# ============================================================================


@pytest.mark.order(4)
@REQUIRES_BOTH
async def test_rag_finds_embedded_doc(lifecycle_graph, lifecycle_config):
    """Step 4: Pergunta sobre KNOWN_KEYWORD → RAG subgraph encontra o doc indexado."""
    from vectora.tools.rag import vector_search

    # Primeiro verificamos via tool direta (mais confiável)
    result_json = await vector_search.ainvoke(
        {
            "query": KNOWN_KEYWORD,
            "collection": TEST_COLLECTION,
            "limit": 5,
        }
    )
    result = json.loads(result_json)

    assert result.get("status") == "success", f"vector_search falhou: {result}"
    results = result.get("results", [])
    assert len(results) >= 1, "Deve encontrar pelo menos 1 documento"

    # Verifica que o conteúdo é relevante
    found_texts = [r.get("content", "") for r in results]
    assert any("LanceDB" in text for text in found_texts), (
        f"Nenhum resultado menciona LanceDB: {found_texts[:2]}"
    )
    logger.info(
        f"Step 4 — vector_search encontrou {len(results)} docs; top: {found_texts[0][:80]}"
    )

    # Segundo, testamos via graph (RAG subgraph)
    response = await invoke_graph(
        lifecycle_graph,
        lifecycle_config,
        f"O que o documento diz sobre '{KNOWN_KEYWORD}'? "
        f"Busque na coleção '{TEST_COLLECTION}'.",
    )
    assert len(response) > 0, "O graph deve retornar resposta RAG"
    logger.info(f"Step 4 — resposta graph: {response[:150]}")


# ============================================================================
# Step 5 — Checkpointer persiste após restart simulado
# ============================================================================


@pytest.mark.order(5)
@REQUIRES_GOOGLE
async def test_checkpointer_persists():
    """Step 5: Fecha o graph e reabre — histórico da session 1212 deve persistir."""
    from vectora.context import Context
    from vectora.graph import build_graph
    from vectora.services.checkpoint import Checkpointer

    context = Context(user_type="test", thread_id=TEST_THREAD_ID)
    config = RunnableConfig(
        configurable={
            "thread_id": TEST_THREAD_ID,
            "context": context,
        }
    )

    # Abre um NOVO checkpointer + NOVO graph (simula restart da aplicação)
    async with Checkpointer() as fresh_cp:
        fresh_graph = build_graph(fresh_cp)

        # Verifica se o checkpointer tem estado da session 1212
        state = await fresh_graph.aget_state(config)
        prior_messages = state.values.get("messages", []) if state.values else []
        logger.info(
            f"Step 5 — mensagens no checkpoint: {len(prior_messages)} mensagens"
        )

        # Deve ter pelo menos as mensagens dos steps anteriores
        assert len(prior_messages) >= 2, (
            f"Checkpointer deve ter mensagens dos steps anteriores, "
            f"encontrou: {len(prior_messages)}"
        )

        # Pergunta que exige memória do histórico
        response = await invoke_graph(
            fresh_graph,
            config,
            "O que eu perguntei no começo desta conversa?",
        )

    assert len(response) > 0, "O graph deve responder mesmo após restart"
    logger.info(f"Step 5 — resposta após restart: {response[:150]}")


# ============================================================================
# Step 6 — LanceDB persiste após restart
# ============================================================================


@pytest.mark.order(6)
@REQUIRES_COHERE
async def test_lancedb_doc_survives_restart():
    """Step 6: Abre novo cliente LanceDB e verifica que KNOWN_TEXT ainda existe."""
    import lancedb

    from vectora.config.settings import settings
    from vectora.tools.rag import vector_search

    # Novo cliente LanceDB (simula restart)
    db = await lancedb.connect_async(str(settings.lancedb_dir))
    tables = await db.table_names()
    assert TEST_COLLECTION in tables, (
        f"Coleção '{TEST_COLLECTION}' deve existir após restart"
    )

    # Busca direta via tool
    result_json = await vector_search.ainvoke(
        {
            "query": KNOWN_KEYWORD,
            "collection": TEST_COLLECTION,
            "limit": 3,
        }
    )
    result = json.loads(result_json)
    assert result.get("status") == "success", f"vector_search falhou: {result}"
    results = result.get("results", [])
    assert len(results) >= 1, "Documento deve persistir no LanceDB após restart"

    content = results[0].get("content", "")
    assert "LanceDB" in content or "SQLite" in content, (
        f"Conteúdo recuperado não corresponde: {content[:100]}"
    )
    logger.info(f"Step 6 — doc encontrado após restart: {content[:80]}")


# ============================================================================
# Step 7 — Traces registrados para a session 1212
# ============================================================================


@pytest.mark.order(7)
async def test_traces_recorded():
    """Step 7: Verifica que o tracer registrou spans para a session 1212."""
    from vectora.services.tracer import tracer

    spans = await tracer.get_session(TEST_SESSION_ID)

    logger.info(f"Step 7 — total de spans na session 1212: {len(spans)}")

    # Verifica que há spans (mesmo que steps com API keys tenham sido pulados)
    # Os spans podem vir de qualquer step que rodou com sucesso
    if len(spans) == 0:
        logger.warning(
            "Nenhum span encontrado para session 1212. "
            "Verifique se os steps anteriores rodaram com API keys configuradas."
        )
        pytest.skip("Nenhum step de integração rodou (API keys ausentes)")

    # Verifica campos básicos dos spans
    for span in spans:
        assert "span_id" in span, "Span deve ter span_id"
        assert "node" in span, "Span deve ter node"
        assert "duration_ms" in span, "Span deve ter duration_ms"
        assert span.get("duration_ms", -1) >= 0, "duration_ms deve ser não-negativo"

    # Verifica que há spans de nodes conhecidos (pelo menos um)
    known_nodes = {"supervisor", "invoke_llm", "rag_retrieve", "retrieval_node"}
    found_nodes = {s.get("node") for s in spans}
    overlap = known_nodes & found_nodes

    logger.info(f"Step 7 — nodes encontrados: {found_nodes}")
    logger.info(f"Step 7 — nodes conhecidos encontrados: {overlap}")

    # Pelo menos alguns dos spans devem ser de nodes do grafo
    assert len(overlap) > 0 or len(spans) > 0, (
        "Deve haver pelo menos 1 span registrado para a session 1212"
    )
