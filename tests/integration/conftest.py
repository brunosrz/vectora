"""Fixtures compartilhadas para testes de integração — session 1212.

Todos os testes de integração usam a session 1212 como thread_id fixo.
A fixture `integration_cleanup` limpa os dados desta session antes da suite.
"""

from __future__ import annotations

import asyncio
import logging

import pytest
from langchain_core.messages import HumanMessage
from langgraph.graph.state import RunnableConfig

logger = logging.getLogger(__name__)

# ============================================================================
# Constants exportadas — use em test_lifecycle.py e test_mcp_tools.py
# ============================================================================

TEST_THREAD_ID = "1212"
TEST_SESSION_ID = 1212
TEST_COLLECTION = "test_lifecycle_1212"

# Texto determinístico — sempre o mesmo para garantir reprodutibilidade
KNOWN_TEXT = (
    "O Vectora usa LanceDB como banco vetorial e SQLite para checkpoints de sessão."
)
KNOWN_KEYWORD = "LanceDB banco vetorial"

# Marcadores de skip baseados em env vars
REQUIRES_GOOGLE = pytest.mark.skipif(
    not __import__("os").getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY não configurado",
)
REQUIRES_COHERE = pytest.mark.skipif(
    not __import__("os").getenv("COHERE_API_KEY"),
    reason="COHERE_API_KEY não configurado",
)
REQUIRES_BOTH = pytest.mark.skipif(
    not __import__("os").getenv("GOOGLE_API_KEY")
    or not __import__("os").getenv("COHERE_API_KEY"),
    reason="GOOGLE_API_KEY e COHERE_API_KEY são necessários",
)


# ============================================================================
# Limpeza da session 1212 — roda UMA VEZ antes da suite de integração
# ============================================================================


async def _cleanup_session_1212() -> None:
    """Remove dados de teste da session 1212: checkpoints + LanceDB + traces."""
    from src.settings import settings

    # 1. Limpa checkpoints SQLite (tabelas checkpoints + writes do LangGraph)
    try:
        import aiosqlite

        if settings.db_dsn is None:
            raise RuntimeError("db_dsn not configured")
        async with aiosqlite.connect(settings.db_dsn) as db:
            await db.execute(
                "DELETE FROM checkpoints WHERE thread_id=?", (TEST_THREAD_ID,)
            )
            await db.execute("DELETE FROM writes WHERE thread_id=?", (TEST_THREAD_ID,))
            await db.commit()
        logger.info("Checkpoints da session 1212 limpos")
    except Exception as e:
        logger.warning(f"Não foi possível limpar checkpoints: {e}")

    # 2. Limpa coleção LanceDB de teste
    try:
        import lancedb

        from src.settings import settings as s

        db_lance = await lancedb.connect_async(str(s.lancedb_dir))
        tables = await db_lance.table_names()
        if TEST_COLLECTION in tables:
            await db_lance.drop_table(TEST_COLLECTION)
            logger.info(f"Coleção LanceDB '{TEST_COLLECTION}' removida")
    except Exception as e:
        logger.warning(f"Não foi possível limpar LanceDB: {e}")

    # 3. Limpa traces da session 1212
    try:
        from src.services.tracer import tracer

        removed = await tracer.clear_session(TEST_SESSION_ID)
        logger.info(f"Traces da session 1212 removidos: {removed}")
    except Exception as e:
        logger.warning(f"Não foi possível limpar traces: {e}")


@pytest.fixture(scope="session", autouse=False)
def integration_cleanup() -> None:  # type: ignore[return]
    """Limpeza síncrona (scope=session) — chame explicitamente nos testes de integração.

    Usa asyncio.run() para não conflitar com o event loop do pytest-asyncio.
    """
    asyncio.run(_cleanup_session_1212())


# ============================================================================
# Fixtures de graph — function scope (uma conexão por teste)
# ============================================================================


@pytest.fixture
async def lifecycle_graph():
    """Graph com checkpointer real (settings.db_dsn) para testes de lifecycle.

    Cada teste abre e fecha sua própria conexão SQLite, mas compartilham o
    mesmo arquivo de banco — portanto o histórico persiste entre testes.
    """
    from src.graph import build_graph
    from src.services.checkpoint import Checkpointer

    async with Checkpointer() as cp:
        graph = build_graph(cp)
        yield graph


@pytest.fixture
def lifecycle_config() -> RunnableConfig:
    """RunnableConfig para session 1212 com Context correto."""
    from src.context import Context

    context = Context(user_type="test", thread_id=TEST_THREAD_ID)
    return RunnableConfig(
        configurable={
            "thread_id": TEST_THREAD_ID,
            "context": context,
        }
    )


# ============================================================================
# Helpers exportados — importáveis nos arquivos de teste
# ============================================================================


async def invoke_graph(graph, config: RunnableConfig, user_input: str) -> str:
    """Invoca o graph e retorna a resposta de texto do assistente.

    Extrai o último AIMessage (ou mensagem não-Human) do estado resultante.
    """
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "session_metadata": {"thread_id": TEST_SESSION_ID},
        },
        config=config,
    )
    messages = result.get("messages", [])
    for msg in reversed(messages):
        if not isinstance(msg, HumanMessage) and hasattr(msg, "content"):
            content = msg.content
            if isinstance(content, list):
                # Gemini retorna lista de dicts com "text"
                return " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content
                )
            return str(content)
    return ""


async def embed_direct(text: str, collection: str) -> None:
    """Embeda texto diretamente no LanceDB (bypass da fila — só para testes).

    Usa BackgroundEmbeddingWorker internamente para garantir o mesmo schema
    que o sistema real usa em produção.
    """
    from uuid import uuid4

    from src.services.background import BackgroundEmbeddingWorker
    from src.services.queue import EmbeddingQueueRecord

    worker = BackgroundEmbeddingWorker()
    vector = await worker._generate_embedding(text)

    record = EmbeddingQueueRecord(
        queue_id=str(uuid4()),
        text=text,
        collection=collection,
        doc_metadata="{}",
    )
    await worker._write_to_lancedb(record, vector)
