"""LangGraph State Definition and Message Management.

Defines the state schema for conversation: messages, summary, retrieval results.
Includes reducer for message deduplication and history management.
"""

from collections.abc import Sequence
from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from vectora.types import (
    ArtifactMetadata,
    CoderResult,
    ParallelResult,
    SearchResult,
    SubTask,
    UIMetrics,
)


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
    - workspace_id: ID do workspace ativo (sha256[:8] do cwd)
    - manifest_version: Versão do manifest carregada no contexto desta sessão
    """

    thread_id: str  # 6-digit zero-padded string, e.g. '042731'
    user_type: str
    created_at: str  # ISO 8601
    llm_provider: str
    llm_model: str
    workspace_id: str  # ID do workspace ativo (B5)
    manifest_version: int  # Versão do manifest no contexto (B7 — invalidação)


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
        Literal["direct", "coder", "search", "tools", "rag", "parallel"] | None
    ]

    # Pipeline de RAG
    rag_query: NotRequired[str | None]  # Query extraída para busca vetorial
    rag_docs: NotRequired[
        list[Document] | None
    ]  # Documentos recuperados pelo subgrafo RAG
    rag_query_variants: NotRequired[
        list[str] | None
    ]  # C2 — variantes da query geradas pelo LLM para multi-query retrieval
    pending_embeds: NotRequired[
        list[str] | None
    ]  # queue_ids do fire-and-forget para rastreamento
    web_search_triggered: NotRequired[
        bool | None
    ]  # Flag: web_search foi acionado no ciclo atual
    rag_pending: NotRequired[
        bool | None
    ]  # Flag: search foi invocado pelo pipeline RAG (score baixo)
    # Quando True, search_finalize roteia para rag_inject em vez do orchestrator.

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

    # HITL — Human-in-the-Loop
    # Definido pelo nó hitl_check ao retomar após interrupt():
    #   False → ação aprovada, seguir para coder_tools
    #   True  → ação rejeitada, seguir de volta ao coder com msgs de cancelamento
    hitl_cancelled: NotRequired[bool | None]

    # Resultados estruturados dos sub-agents (B2 — Structured Outputs)
    # Produzidos por coder_finalize / search_finalize antes de retornar ao orchestrator.
    # O orchestrator lê esses campos para síntese final e os zera após uso.
    coder_result: NotRequired[CoderResult | None]
    search_result: NotRequired[SearchResult | None]

    # Execução paralela de agentes (C5)
    # parallel_tasks: lista de SubTasks emitidas pelo orchestrator
    # parallel_results: resultados coletados por parallel_dispatch antes de síntese
    parallel_tasks: NotRequired[list[SubTask] | None]
    parallel_results: NotRequired[list[ParallelResult] | None]

    # Métricas de observabilidade em tempo real (D1.5 — State-Sync Observability)
    # Atualizadas pelos nós principais via Command(update={"ui_metrics": ...}).
    # Consumidas pela Web UI (MetricsPanel.tsx) sem polling — chegam via SSE stream.
    # Campos:
    #   last_node: nó que acabou de executar
    #   last_node_ms: latência em ms desse nó
    #   total_tokens_session: tokens acumulados na sessão
    #   rag_hits: buscas RAG que retornaram documentos relevantes
    #   rag_misses: fallbacks para websearch por score < threshold
    #   tool_calls: {tool_name: count} de chamadas nesta sessão
    #   workspace_id: workspace ativo (espelha session_metadata.workspace_id)
    #   manifest_version: versão do manifest carregado (espelha session_metadata)
    ui_metrics: NotRequired[UIMetrics | None]

    # Bloco D — Reasoning Reveal
    # Raciocínio do orchestrator para o turno atual.
    # Escrito pelo nó orchestrator antes de retornar; consumido por adapt_stream
    # para emitir ThinkingEvent via SSE.  Zerado a cada turno.
    thinking: NotRequired[dict | None]
