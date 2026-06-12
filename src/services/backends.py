"""Backends pluggable do Vectora — CompositeBackend canônico.

Monta e expõe o ``CompositeBackend`` passado a ``create_deep_agent(backend=...)``.
O harness deepagents usa este backend para persistir e recuperar artifacts,
histórico de mensagens comprimido, e arquivos do workspace.

Rotas configuradas:
    /workspace/     → FilesystemBackend(root_dir=workspace_path)
                      Acesso ao filesystem do workspace ativo do usuário.
    /memories/      → StoreBackend(namespace=user_ns)
                      Armazenamento de memórias do usuário no LangGraph Store.
    /skills/        → StoreBackend(namespace=skills_ns)
                      Armazenamento de skills do usuário.
    /large_tool_results/ → StateBackend()
                      Resultados grandes de tools armazenados no grafo (evita
                      inflar o contexto com outputs volumosos).

O ``StateBackend`` é usado como default (fallback para paths não roteados).

Nota: nossa camada de tools artesanais (``src/tools/fs.py``) continua ativa —
coexiste com o ``FilesystemBackend`` que o harness usa internamente.
A migração completa para tools automáticas via ``FilesystemMiddleware``
está planejada para uma fase posterior.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Factory de CompositeBackend
# ---------------------------------------------------------------------------


def build_backend(
    workspace_id: str | None = None,
    user_id: str | None = None,
) -> Any:
    """Constrói ``CompositeBackend`` para uma sessão do usuário.

    Args:
        workspace_id: ID do workspace ativo. Se None, o ``FilesystemBackend``
            aponta para o diretório home como fallback seguro.
        user_id: ID do usuário para namespacing das memórias no Store.

    Returns:
        ``CompositeBackend`` configurado com rotas /workspace/, /memories/,
        /skills/ e /large_tool_results/.

    Raises:
        ImportError: Se deepagents não estiver instalado.
    """
    from deepagents.backends import (
        CompositeBackend,
        FilesystemBackend,
        StateBackend,
        StoreBackend,
    )

    # ── Workspace backend ─────────────────────────────────────────────────────
    workspace_root = _resolve_workspace_root(workspace_id)
    fs_backend = FilesystemBackend(root_dir=workspace_root)

    # ── State backend (default + large results) ───────────────────────────────
    state_backend = StateBackend()

    # ── Store backends (memories + skills) ───────────────────────────────────
    uid = user_id or "local"

    def _memory_namespace(runtime: Any) -> tuple[str, ...]:
        return ("user", uid, "memories")

    def _skills_namespace(runtime: Any) -> tuple[str, ...]:
        return ("user", uid, "skills")

    memories_backend = StoreBackend(namespace=_memory_namespace)
    skills_backend = StoreBackend(namespace=_skills_namespace)

    # ── Composite ─────────────────────────────────────────────────────────────
    backend = CompositeBackend(
        default=state_backend,
        routes={
            "/workspace/": fs_backend,
            "/memories/": memories_backend,
            "/skills/": skills_backend,
            "/large_tool_results/": state_backend,
        },
    )

    logger.debug(
        "backends: CompositeBackend criado workspace_root=%s user_id=%s",
        workspace_root,
        uid,
    )
    return backend


async def build_store(embedding_model: str | None = None) -> Any:
    """Constrói o ``AsyncSqliteStore`` (F5) persistente com embeddings Cohere opcionais.

    Abre uma conexão ``aiosqlite`` dedicada (isolation_level=None + WAL) e cria
    ``AsyncSqliteStore(conn, index=index)``. A conexão fica armazenada em
    ``store.conn`` — enquanto o store estiver vivo, a conexão permanece aberta.
    Chama ``await store.setup()`` para criar as tabelas LangGraph na primeira vez.

    Usado como ``store=`` em ``create_deep_agent`` e disponível às tools via
    ``langgraph.config.get_store()`` dentro do grafo. O store persiste memórias
    do agente em SQLite (lite mode).

    Args:
        embedding_model: Nome do modelo de embedding para busca semântica.
            Se None, tenta ``settings.embedding_model``; se não configurado,
            o store funciona sem indexação vetorial (busca por chave apenas).

    Returns:
        ``AsyncSqliteStore`` pronto para ser passado a ``create_deep_agent``.

    Nota:
        Usa uma conexão própria (não o pool F1) porque ``AsyncSqliteStore``
        mantém o ``conn`` aberto pelo ciclo de vida do processo. O pool F1
        é reservado para o checkpointer (acesso transacional curto).
    """
    import aiosqlite
    from langgraph.store.sqlite.aio import AsyncSqliteStore

    index = _build_index(embedding_model)

    try:
        from src.settings import settings as _settings

        db_path = _settings.db_dsn or ""
    except Exception:
        db_path = ""

    if not db_path:
        import tempfile

        db_path = str(Path(tempfile.gettempdir()) / "vectora_store.db")
        logger.debug("backends: store db_path fallback para %s", db_path)

    # Garante que o diretório existe
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Abre conexão persistente com WAL para suportar leituras concorrentes
    # com o checkpointer no mesmo arquivo SQLite.
    conn = await aiosqlite.connect(db_path, isolation_level=None)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA synchronous=NORMAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")

    store = AsyncSqliteStore(conn, index=index)
    await store.setup()

    logger.debug(
        "backends: AsyncSqliteStore criado path=%s index=%s",
        db_path,
        "Cohere" if index else "none",
    )
    return store


def _build_index(embedding_model: str | None) -> Any:
    """Constrói IndexConfig com ``CohereEmbeddings`` (langchain-cohere) se disponível.

    Usa ``CohereEmbeddings.aembed_documents()`` via langchain-cohere em vez de
    ``cohere.AsyncClient`` direto, alinhando com o SDK oficial (F15).
    Retorna None se a chave Cohere ou o modelo não estiverem configurados.
    """
    try:
        from langchain_cohere import CohereEmbeddings

        from src.settings import settings as _settings

        model = embedding_model or _settings.embedding_model
        cohere_key = _settings.get_cohere_api_key()
        if not cohere_key or not model:
            return None

        # Captura por valor para evitar referência ao escopo externo
        _model = model
        _key = cohere_key

        # Instância CohereEmbeddings com o SDK oficial langchain-cohere.
        # NOTE: NÃO usar SecretStr — a lib chama str() internamente, resultando
        # em "**********" como API key. Passar a string diretamente.
        # NOTE: CohereEmbeddings stubs exigem client/async_client que são
        # opcionais em runtime. Mesmo padrão de src/services/background.py.
        _embeddings = CohereEmbeddings(  # ty: ignore[missing-argument]
            cohere_api_key=_key,  # ty: ignore[invalid-argument-type]
            model=_model,
        )

        async def _embed(texts: list[str]) -> list[list[float]]:
            return await _embeddings.aembed_documents(texts)

        return {"dims": 1024, "embed": _embed, "fields": ["content"]}
    except ImportError:
        logger.debug(
            "backends: langchain-cohere não instalado — InMemoryStore sem índice vetorial"
        )
        return None
    except Exception:
        logger.debug(
            "backends: Cohere indisponível — InMemoryStore sem índice vetorial",
            exc_info=True,
        )
        return None


def build_backend_lazy() -> Any:
    """Retorna uma factory de backend (callable) para injeção lazy no grafo.

    Quando passada como ``backend=build_backend_lazy()`` ao ``create_deep_agent``,
    a factory é chamada com o ``ToolRuntime`` no início de cada turno, permitindo
    que o workspace_id e user_id sejam lidos do contexto em tempo real via
    ``runtime.context`` (disponível após E.B-5).

    Por ora usa ``workspace_id=None`` (filesystem root padrão) e ``user_id`` do
    context se disponível; migração completa em E.B-11 quando VectoraContext
    estiver integrado em todas as tools.
    """

    def _factory(runtime: Any) -> Any:
        ctx = getattr(runtime, "context", None)
        workspace_id = getattr(ctx, "workspace_id", None) or None
        user_id = getattr(ctx, "user_id", None) or "local"
        return build_backend(workspace_id=workspace_id, user_id=user_id)

    return _factory


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _resolve_workspace_root(workspace_id: str | None) -> Path:
    """Resolve o path raiz do filesystem backend para o workspace.

    Busca o workspace no registry; se não encontrar, usa o diretório
    de workspaces padrão (~/.vectora/workspaces/<workspace_id>).
    Fallback para o home do usuário se workspace_id for None/vazio.
    """
    if not workspace_id:
        return Path.home()

    try:
        from src.services.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        if ws and ws.cwd:
            return Path(ws.cwd)
    except Exception:
        pass

    # Fallback: diretório padrão de workspaces
    default_path = Path.home() / ".vectora" / "workspaces" / workspace_id
    if default_path.exists():
        return default_path

    return Path.home()
