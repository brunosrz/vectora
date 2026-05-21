"""LangGraph State Definition and Message Management.

Defines the state schema for conversation: messages, summary, retrieval results.
Includes reducer for message deduplication and history management.
"""

from collections.abc import Sequence
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from vectora.messages import ArtifactMetadata


class Document(TypedDict, total=False):
    """Estrutura de documento recuperado do RAG."""

    page_content: str
    metadata: dict[str, Any]
    relevance_score: float | None


class SessionMetadata(TypedDict, total=False):
    """Session metadata for context tracking (JSON-serializable).

    Replaces complex Context object in RunnableConfig.
    All fields are immutable and part of State (JSON-safe).

    Fields:
    - thread_id: Unique session identifier
    - user_type: User classification (default or custom)
    - created_at: ISO 8601 timestamp
    - llm_provider: Active LLM provider (google-genai, openai, etc.)
    - llm_model: Active model name
    """

    thread_id: str  # 6-digit zero-padded string, e.g. '042731'
    user_type: str
    created_at: str  # ISO 8601
    llm_provider: str
    llm_model: str


class State(TypedDict):
    """Estado da conversa com suporte a RAG e histórico gerenciado pelo LangGraph.

    O reducer nativo `add_messages` substitui qualquer lógica manual de sliding window.
    Ele realiza append inteligente, suporta substituição de mensagem por `id` e é
    mantido pela equipe LangChain — tornando-o a fonte da verdade do histórico.

    Session metadata (thread_id, user_type, etc.) agora faz parte do State,
    tornando o estado JSON-serializable. Remova Context do RunnableConfig.

    Campos obrigatórios:
    - messages: Histórico gerenciado por `add_messages` (append automático)
    - session_metadata: Session context (thread_id, user_type, timestamps)

    Campos opcionais:
    - Contexto RAG, routing metadata, histórico resumido
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_metadata: SessionMetadata

    # Campos transitórios — ativamente usados por nodes/base.py, nodes/engine.py e mcp/server.py.
    # TODO (Phase 5 refactor): migrar para rag_docs + session_metadata e remover estes campos.
    retrieval_results: NotRequired[dict[str, list[Document]] | None]
    selected_rag_source: NotRequired[str | None]
    summarized_history: NotRequired[str | None]

    # Roteamento determinístico
    routing_decision: NotRequired[
        Literal["direct", "coder", "search", "tools", "rag"] | None
    ]

    # Pipeline de RAG
    rag_query: NotRequired[str | None]  # Query extraída para busca vetorial
    rag_docs: NotRequired[
        list[Document] | None
    ]  # Documentos recuperados pelo subgrafo RAG
    pending_embeds: NotRequired[
        list[str] | None
    ]  # queue_ids do fire-and-forget para rastreamento
    web_search_triggered: NotRequired[
        bool | None
    ]  # Flag: web_search foi acionado no ciclo atual

    # Artifacts gerados na sessão (planos, specs, guias)
    # Persistidos em ~/.vectora/artifacts/{session_id}/{slug}.md
    # Nunca enviados ao LLM — apenas metadados para o orchestrator
    artifacts: NotRequired[list[ArtifactMetadata] | None]

    # Task query do orchestrator para sub-agents
    # Quando o orchestrator delega, escreve aqui uma instrução clara e concisa
    # O sub-agent (coder/search) lê este campo e prioriza sobre o histórico bruto
    orchestrator_task: NotRequired[str | None]

    # Contexto do projeto carregado na primeira mensagem da sessão
    # Conteúdo concatenado de AGENTS.md, CLAUDE.md, GEMINI.md encontrados no cwd
    # Persistido no checkpoint para não re-escanear a cada turno
    # None = já foi tentado e não encontrou nada; ausente = ainda não tentou
    project_context: NotRequired[str | None]
