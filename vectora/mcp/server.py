"""Vectora MCP Server: Exposes Vectora tools and resources via Model Context Protocol.

This is the production-ready MCP server that Claude Desktop / Claude Code connects to.
It bridges Vectora's internal tools to the MCP protocol using FastMCP.

Transport: stdio JSON-RPC (standard for local MCP servers)
Protocol: MCP (Model Context Protocol)

Entry point: vectora-mcp → vectora.mcp.server:run
"""

import contextlib
import json
import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Logging to file only — never pollute stdout (JSON-RPC channel)
_log_dir = Path.home() / ".vectora" / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(_log_dir / "mcp.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("vectora.mcp.server")

try:
    from mcp.server.fastmcp import FastMCP

    from vectora.config.settings import settings
    from vectora.services.checkpoint import Checkpointer
    from vectora.tools import (
        call_mcp_tool,
        embedding,
        fetch_url,
        file_edit,
        file_read,
        file_write,
        grep,
        ingest_docs,
        list_dir,
        manage_retriever,
        terminal,
        vector_search,
        web_search,
    )
    from vectora.tools.workspace import (
        bucket_summary,
        workspace_describe,
        workspace_list,
    )
except ImportError:
    logger.exception("Failed to import Vectora dependencies")
    sys.exit(1)

# ============================================================================
# LIFESPAN — cleanup garantido na saída do servidor
# ============================================================================


@asynccontextmanager
async def _mcp_lifespan(server: object) -> AsyncGenerator[None]:
    """Context manager de ciclo de vida para o servidor MCP."""
    from vectora.mcp.env_bootstrap import bootstrap_env_from_mcp, validate_required_keys

    bootstrapped = bootstrap_env_from_mcp()
    if bootstrapped:
        logger.info("MCP lifespan: keys persistidas a partir de variáveis de ambiente")

    missing = validate_required_keys()
    if missing:
        logger.warning(
            "MCP lifespan: keys obrigatórias ausentes: %s — "
            "configure-as em ~/.vectora/.env ou passe como variáveis de ambiente",
            ", ".join(missing),
        )

    try:
        yield
    finally:
        logger.info("MCP lifespan: servidor encerrado")


# ============================================================================
# MCP SERVER INSTANCE
# ============================================================================

mcp = FastMCP(
    "Vectora",
    lifespan=_mcp_lifespan,
    instructions=(
        "Vectora é um agente de IA avançado com RAG, busca vetorial, "
        "manipulação de arquivos e capacidades de embedding.\n\n"
        "QUANDO USAR CADA FERRAMENTA:\n\n"
        "🌐 WEB SEARCH (web_search_tool):\n"
        "- Buscar informações ATUAIS e em tempo real da internet\n"
        "- Quando o usuário pergunta sobre notícias, eventos recentes, dados de hoje\n"
        "- NÃO usar para informações já indexadas no Vectora\n\n"
        "📚 VECTOR SEARCH (vector_search_tool):\n"
        "- Buscar documentos/conhecimento JÁ INDEXADO no Vectora\n"
        "- Busca semântica em base de conhecimento persistente\n"
        "- Usa reranking automático para melhor relevância\n"
        "- Preferir sobre web_search quando informação já foi ingerida\n\n"
        "📄 FILE TOOLS (file_read, file_edit, file_write):\n"
        "- file_read: Ler arquivos do disco (projetos, docs, código)\n"
        "- file_edit: Editar trecho específico com replace_all para múltiplas ocorrências\n"
        "- file_write: Criar novo arquivo ou sobrescrever completo\n\n"
        "⚙️ EMBEDDING (embedding_tool):\n"
        "- Indexar novo documento no Vectora para busca semântica futura\n"
        "- Fire-and-forget: retorna queue_id, processa em background\n"
        "- Usar ANTES de vector_search se novo conteúdo foi adicionado\n\n"
        "🔍 INGEST (ingest_docs_tool):\n"
        "- Indexar pasta inteira de documentos de uma vez\n"
        "- Ideal para popular conhecimento base (docs, wiki, code)\n"
        "- Processa em batch com splitting automático\n\n"
        "🌐 FETCH URL (fetch_url_tool):\n"
        "- Extrair conteúdo textual de UMA URL específica\n"
        "- Use quando precisa ler um artigo/doc específico\n"
        "- Melhor que web_search quando você já sabe a URL\n\n"
        "FLUXO RECOMENDADO:\n"
        "1. Entender a pergunta do usuário\n"
        "2. SE é tarefa COMPLEXA (múltiplas etapas, análise profunda) → delegate_task_to_vectora\n"
        "3. SE é tarefa SIMPLES (ferramenta única) → chamar ferramenta específica\n"
        "4. Sempre verificar resources primeiro: /vectora/thread/{id}/history\n\n"
        "⚡ WHEN TO USE EACH MODE:\n"
        "- delegate_task_to_vectora: RAG + análise + síntese, decisões complexas\n"
        "- Ferramentas individuais: quando sabe exatamente qual tool chamar"
    ),
)

logger.info("Vectora MCP server initialized with FastMCP")


# ============================================================================
# TOOL TIMEOUTS (proteção contra travamentos)
# ============================================================================

TOOL_TIMEOUTS = {
    "web_search": 30.0,  # 30 segundos para busca web
    "fetch_url": 30.0,  # 30 segundos para extrair URL
    "vector_search": 20.0,  # 20 segundos para busca vetorial
    "embedding": 60.0,  # 60 segundos para embedding (fire-and-forget)
    "ingest_docs": 120.0,  # 2 minutos para ingestão em batch
    "manage_retriever": 30.0,  # 30 segundos para listar/remover do RAG
    "workspace_describe": 5.0,  # 5 segundos — leitura de arquivo local
    "workspace_list": 5.0,  # 5 segundos — leitura de arquivo local
    "bucket_summary": 5.0,  # 5 segundos — leitura de arquivo local
    "file_read": 10.0,  # 10 segundos para ler arquivo
    "file_edit": 15.0,  # 15 segundos para editar arquivo
    "file_write": 15.0,  # 15 segundos para escrever arquivo
    "grep": 20.0,  # 20 segundos para grep
    "list_dir": 10.0,  # 10 segundos para listar diretório
    "terminal": 60.0,  # 60 segundos para comando terminal
    "call_mcp_tool": 45.0,  # 45 segundos para chamar outro MCP
}


async def _with_timeout(
    coro: object,
    tool_name: str,
    default_timeout: float = 30.0,
) -> str:
    """Executa corrotina com timeout e trata exceções.

    Args:
        coro: Corrotina a executar
        tool_name: Nome da ferramenta (para logs)
        default_timeout: Timeout padrão em segundos

    Returns:
        Resultado da corrotina ou mensagem de erro
    """
    import asyncio

    from vectora.services.tracer import tracer

    timeout = TOOL_TIMEOUTS.get(tool_name, default_timeout)

    try:
        async with tracer.span("mcp_tool", tool_name) as s:
            try:
                result = await asyncio.wait_for(coro, timeout=timeout)  # ty: ignore[invalid-argument-type]
                return str(result)
            except TimeoutError:
                logger.warning(f"Tool timeout: {tool_name} excedeu {timeout}s")
                s.set(status="timeout")
                return f"Erro: Ferramenta '{tool_name}' excedeu timeout de {timeout}s. Tente novamente."
            except Exception as e:
                logger.exception(f"Tool error: {tool_name}", extra={"error": str(e)})
                s.set(status="error", error_type=type(e).__name__)
                return f"Erro na ferramenta '{tool_name}': {type(e).__name__}: {e!s}"
    except Exception:
        # Fallback se o próprio tracer falhar
        timeout = TOOL_TIMEOUTS.get(tool_name, default_timeout)
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)  # ty: ignore[invalid-argument-type]
            return str(result)
        except TimeoutError:
            return f"Erro: Ferramenta '{tool_name}' excedeu timeout de {timeout}s. Tente novamente."
        except Exception as e:
            return f"Erro na ferramenta '{tool_name}': {type(e).__name__}: {e!s}"


# ============================================================================
# TOOLS — Bridge between LangChain tools and MCP protocol
# ============================================================================
# FastMCP automatically converts tool descriptions to MCP tool definitions.
# We wrap each LangChain tool em @mcp.tool() async function with timeouts.


@mcp.tool()
async def web_search_tool(query: str) -> str:
    """Busca informações atuais na web.

    Use para obter notícias recentes, dados atualizados ou qualquer
    informação que não esteja no conhecimento base do modelo.

    Args:
        query: Consulta de busca em linguagem natural

    Returns:
        Resultados da busca formatados como texto
    """
    return await _with_timeout(
        web_search.ainvoke({"query": query}),
        "web_search",
    )


@mcp.tool()
async def fetch_url_tool(url: str) -> str:
    """Busca e extrai o conteúdo textual de uma URL.

    Use para ler artigos, documentações ou qualquer página web específica.

    Args:
        url: URL completa para buscar (https://...)

    Returns:
        Conteúdo textual extraído da página
    """
    return await _with_timeout(
        fetch_url.ainvoke({"url": url}),
        "fetch_url",
    )


@mcp.tool()
async def vector_search_tool(
    query: str,
    collection: str = "default",
    limit: int = 5,
) -> str:
    """Busca documentos semanticamente similares no banco vetorial LanceDB.

    Use para encontrar informações já indexadas via embedding no Vectora.

    Args:
        query: Consulta em linguagem natural
        collection: Nome da coleção (default: "default")
        limit: Número máximo de resultados (default: 5)

    Returns:
        Documentos similares com score de relevância
    """
    return await _with_timeout(
        vector_search.ainvoke(
            {"query": query, "collection": collection, "limit": limit}
        ),
        "vector_search",
    )


@mcp.tool()
async def embedding_tool(
    text: str,
    collection: str = "default",
    metadata: dict | None = None,
) -> str:
    """Enfileira um documento para embedding assíncrono no LanceDB.

    Use para indexar novos documentos no banco vetorial do Vectora.
    O embedding é processado em background pelo worker.

    Args:
        text: Texto do documento para indexar
        collection: Coleção de destino (default: "default")
        metadata: Metadados adicionais (title, source, etc.)

    Returns:
        Confirmação de enfileiramento com ID do documento
    """
    args: dict = {"text": text, "collection": collection}
    if metadata:
        args["metadata"] = metadata
    return await _with_timeout(
        embedding.ainvoke(args),
        "embedding",
    )


@mcp.tool()
async def ingest_docs_tool(
    docs_pattern: str,
    collection: str = "default",
    recursive: bool = True,
) -> str:
    """Ingere múltiplos arquivos em lote no banco vetorial.

    Use para indexar pastas inteiras de documentos de uma vez.

    Args:
        docs_pattern: Padrão glob dos arquivos (ex: "src/**/*.py")
        collection: Coleção de destino (default: "default")
        recursive: Se True, busca recursivamente (default: True)

    Returns:
        Relatório de ingestão com arquivos processados
    """
    return await _with_timeout(
        ingest_docs.ainvoke(
            {
                "docs_pattern": docs_pattern,
                "collection": collection,
                "recursive": recursive,
            }
        ),
        "ingest_docs",
    )


@mcp.tool()
async def manage_retriever_tool(
    action: str,
    collection: str = "web_cache",
    source: str | None = None,
) -> str:
    """Gerencia o RAG: lista, remove ou limpa documentos indexados no LanceDB.

    Use para corrigir a base de conhecimento — remover conteúdo web indexado
    por engano quando a fonte canônica passa a ser conhecida.

    Args:
        action: "list" (lista docs), "delete" (remove por source) ou
            "purge" (apaga a coleção inteira)
        collection: coleção LanceDB alvo (default: "web_cache", o bucket web)
        source: trecho da URL/source a remover — obrigatório para "delete"

    Returns:
        JSON com o resultado da operação
    """
    args: dict = {"action": action, "collection": collection}
    if source:
        args["source"] = source
    return await _with_timeout(
        manage_retriever.ainvoke(args),
        "manage_retriever",
    )


@mcp.tool()
async def workspace_describe_tool(workspace_id: str | None = None) -> str:
    """Descreve o workspace ativo: base de conhecimento indexada, buckets e tópicos.

    Retorna o MANIFEST.md do workspace — resumo gerado automaticamente pelo
    curator de tudo que foi indexado neste projeto.

    Args:
        workspace_id: ID do workspace (None = workspace ativo)

    Returns:
        Conteúdo do MANIFEST.md em markdown, ou mensagem indicando que não há manifest
    """
    args: dict = {}
    if workspace_id:
        args["workspace_id"] = workspace_id
    return await _with_timeout(
        workspace_describe.ainvoke(args),
        "workspace_describe",
    )


@mcp.tool()
async def workspace_list_tool() -> str:
    """Lista todos os workspaces Vectora registrados.

    Retorna ID, nome, caminho e contagem de documentos de cada workspace
    encontrado em ~/.vectora/workspaces.json.

    Returns:
        Listagem formatada de todos os workspaces
    """
    return await _with_timeout(
        workspace_list.ainvoke({}),
        "workspace_list",
    )


@mcp.tool()
async def bucket_summary_tool(bucket: str, workspace_id: str | None = None) -> str:
    """Retorna o resumo de um bucket específico do workspace.

    Lê o arquivo ~/.vectora/workspaces/<id>/buckets/<bucket>.md gerado pelo
    curator após indexação. Útil para entender o conteúdo de um bucket específico.

    Args:
        bucket: Nome do bucket (ex: "code", "docs", "notes", "web_cache")
        workspace_id: ID do workspace (None = workspace ativo)

    Returns:
        Conteúdo do resumo do bucket em markdown
    """
    args: dict = {"bucket": bucket}
    if workspace_id:
        args["workspace_id"] = workspace_id
    return await _with_timeout(
        bucket_summary.ainvoke(args),
        "bucket_summary",
    )


@mcp.tool()
async def file_read_tool(file_path: str) -> str:
    """Lê o conteúdo completo de um arquivo de texto.

    Valida o caminho contra .gitignore para evitar leitura de arquivos sensíveis.

    Args:
        file_path: Caminho absoluto ou relativo do arquivo

    Returns:
        Conteúdo completo do arquivo como string
    """
    return await _with_timeout(
        file_read.ainvoke({"file_path": file_path}),
        "file_read",
    )


@mcp.tool()
async def file_edit_tool(file_path: str, old_text: str, new_text: str) -> str:
    """Edita um arquivo substituindo um trecho de texto por outro.

    Usa correspondência exata de string para localizar e substituir.

    Args:
        file_path: Caminho do arquivo para editar
        old_text: Texto exato a ser substituído
        new_text: Novo texto que substituirá o antigo

    Returns:
        Confirmação da edição realizada
    """
    return await _with_timeout(
        file_edit.ainvoke(
            {"file_path": file_path, "old_text": old_text, "new_text": new_text}
        ),
        "file_edit",
    )


@mcp.tool()
async def file_write_tool(file_path: str, content: str) -> str:
    """Cria ou sobrescreve completamente um arquivo com o conteúdo fornecido.

    Use para criar novos arquivos ou substituir o conteúdo completo de um existente.
    Para edições cirúrgicas (substituir apenas um trecho), prefira file_edit_tool.

    Args:
        file_path: Caminho do arquivo (absoluto ou relativo)
        content: Conteúdo completo a escrever no arquivo

    Returns:
        Confirmação com caminho e tamanho em bytes
    """
    return await _with_timeout(
        file_write.ainvoke({"file_path": file_path, "content": content}),
        "file_write",
    )


@mcp.tool()
async def grep_tool(pattern: str, path: str = ".") -> str:
    """Busca um padrão regex em arquivos.

    Retorna as linhas que correspondem ao padrão com número de linha e arquivo.

    Args:
        pattern: Expressão regular para buscar
        path: Diretório ou arquivo onde buscar (default: ".")

    Returns:
        Linhas correspondentes com contexto (arquivo:linha:conteúdo)
    """
    return await _with_timeout(
        grep.ainvoke({"pattern": pattern, "path": path}),
        "grep",
    )


@mcp.tool()
async def list_dir_tool(path: str = ".", recursive: bool = False) -> str:
    """Lista arquivos e diretórios em um caminho.

    Args:
        path: Caminho do diretório para listar (default: ".")
        recursive: Se True, lista recursivamente (default: False)

    Returns:
        Lista de arquivos e diretórios com metadados
    """
    return await _with_timeout(
        list_dir.ainvoke({"path": path, "recursive": recursive}),
        "list_dir",
    )


@mcp.tool()
async def terminal_tool(command: str) -> str:
    """Executa um comando shell com whitelist de segurança.

    Apenas comandos permitidos pela política de segurança são executados.

    Args:
        command: Comando shell para executar

    Returns:
        Saída do comando (stdout + stderr)
    """
    return await _with_timeout(
        terminal.ainvoke({"command": command}),
        "terminal",
    )


@mcp.tool()
async def call_mcp_tool_tool(tool_name: str, arguments: str) -> str:
    """Invoca uma ferramenta de outro servidor MCP via protocolo MCP.

    Use para encadear chamadas a outros servidores MCP registrados.

    Args:
        tool_name: Nome da ferramenta MCP para invocar
        arguments: Argumentos em formato JSON string

    Returns:
        Resultado da ferramenta MCP invocada
    """
    return await _with_timeout(
        call_mcp_tool.ainvoke({"tool_name": tool_name, "arguments": arguments}),
        "call_mcp_tool",
    )


@mcp.tool()
async def delegate_task_to_vectora(
    task_prompt: str,
    thread_id: int = 1,
) -> str:
    """Delega uma tarefa complexa para o motor de raciocínio do Vectora (A2A).

    MODO SUB-AGENTE: Use quando a tarefa exigir múltiplas etapas de RAG,
    análise de arquivos, busca web ou raciocínio complexo.

    Args:
        task_prompt: Descrição completa da tarefa/pergunta para processar
        thread_id: ID da sessão/conversa para manter contexto (default: 1)

    Returns:
        Resultado final processado pelo LangGraph do Vectora
    """
    if not task_prompt or not task_prompt.strip():
        return "Erro: task_prompt não pode estar vazio"

    logger.info(
        "A2A: delegação recebida (não implementado)",
        extra={"thread_id": thread_id, "prompt_length": len(task_prompt)},
    )

    # A2A ainda não está implementado — o grafo LangGraph real precisa ser
    # exposto via uma interface de execução antes de ser usado aqui.
    # Use as ferramentas individuais (web_search, vector_search, file_read, etc.)
    # enquanto esta integração não estiver pronta.
    return (
        "A2A (Agent-to-Agent) ainda não está disponível nesta versão.\n\n"
        "Use as ferramentas individuais para sua tarefa:\n"
        "- web_search_tool: busca na internet\n"
        "- vector_search_tool: busca no conhecimento indexado\n"
        "- file_read_tool / file_edit_tool: operações em arquivos\n"
        "- terminal_tool: execução de comandos"
    )


@mcp.tool()
async def vectora_metrics(
    n: int = 30,
    node: str | None = None,
) -> str:
    """Retorna métricas de observabilidade do Vectora (spans recentes do tracer).

    Expõe latência por nó, contagem de chamadas e distribuição de status
    das últimas execuções do grafo LangGraph.

    Args:
        n: Número de spans recentes a analisar (default: 30)
        node: Filtrar por nó específico (ex: "orchestrator", "invoke_llm", "rag_retrieve")

    Returns:
        JSON com métricas agregadas: por nó — contagem, latência média/p95, status
    """
    import asyncio

    from vectora.services.tracer import tracer

    try:
        spans = await asyncio.wait_for(tracer.get_recent(n=n), timeout=5.0)
    except Exception as exc:
        return json.dumps({"error": f"Tracer indisponível: {exc}"})

    if node:
        spans = [s for s in spans if s.get("node", "").startswith(node)]

    if not spans:
        return json.dumps({"spans_analyzed": 0, "nodes": {}})

    # Agrega por nó
    nodes: dict[str, dict] = {}
    for sp in spans:
        n_name = sp.get("node", "unknown")
        dur = sp.get("duration_ms")
        status = sp.get("status", "ok")
        in_tok = sp.get("in_tokens") or 0
        out_tok = sp.get("out_tokens") or 0

        entry = nodes.setdefault(
            n_name,
            {
                "count": 0,
                "durations": [],
                "statuses": {},
                "in_tokens": 0,
                "out_tokens": 0,
            },
        )
        entry["count"] += 1
        if dur is not None:
            entry["durations"].append(float(dur))
        entry["statuses"][status] = entry["statuses"].get(status, 0) + 1
        entry["in_tokens"] += in_tok
        entry["out_tokens"] += out_tok

    # Formata métricas finais
    result: dict = {"spans_analyzed": len(spans), "nodes": {}}
    for n_name, data in sorted(nodes.items()):
        durs = sorted(data["durations"])
        avg_ms = round(sum(durs) / len(durs), 1) if durs else None
        p95_ms = round(durs[int(len(durs) * 0.95)], 1) if durs else None
        result["nodes"][n_name] = {
            "count": data["count"],
            "avg_ms": avg_ms,
            "p95_ms": p95_ms,
            "statuses": data["statuses"],
            "total_in_tokens": data["in_tokens"],
            "total_out_tokens": data["out_tokens"],
        }

    return json.dumps(result, ensure_ascii=False)


logger.info("18 tools registered in MCP server")


# ============================================================================
# RESOURCES — Cognitive state of the Vectora agent
# ============================================================================
# Resources expose Vectora's internal state so Claude Code can read context
# before deciding which tool to call.
# Pattern: vectora://<resource>/<id>


@mcp.resource("vectora://tools/schema")
async def get_tools_schema() -> str:
    """Retorna metadados de todas as tools do Vectora, incluindo render_hint para a Web UI.

    O campo `render_hint` em cada tool indica ao frontend como exibir o resultado:
    - search_results: cards com score, fonte e trecho
    - web_results: cards com favicon, URL e snippet
    - diff: unified diff colorido (file_edit)
    - code_block: syntax highlight por extensão (file_read, terminal)
    - terminal_output: fundo escuro, monospace
    - queue_progress: barra de progresso (ingest_docs)
    - queue_badge: badge com queue_id + status (embedding)
    - table: tabela paginada (manage_retriever, workspace_list)
    - markdown: conteúdo Markdown renderizado (workspace_describe, bucket_summary)
    - json: JSON expandível (fallback padrão)

    Returns:
        JSON com lista de tools e seus metadados
    """
    from vectora.nodes.tools import ALL_TOOLS

    tools_data = []
    for t in ALL_TOOLS:
        schema: dict = {}
        try:
            args_schema = getattr(t, "args_schema", None)
            if args_schema is not None and hasattr(args_schema, "model_json_schema"):
                schema = args_schema.model_json_schema()
        except Exception:
            pass
        tools_data.append(
            {
                "name": t.name,
                "description": (t.description or "").split("\n")[0][:200],
                "args_schema": schema,
                "render_hint": (t.extras or {}).get("render_hint", "json"),
            }
        )

    return json.dumps(
        {"version": "1", "tool_count": len(tools_data), "tools": tools_data},
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("vectora://thread/{thread_id}/context")
async def get_thread_context(thread_id: str) -> str:
    """Returns the current context and summary of a Vectora conversation thread.

    Allows Claude Code to read the cognitive state of Vectora before
    deciding which tool to call.

    Args:
        thread_id: Thread/conversation ID

    Returns:
        JSON string with context summary
    """
    logger.info("Resource: get_thread_context(%s)", thread_id)

    try:
        async with Checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": str(thread_id)}}
            values = await checkpointer.aget(config)  # ty: ignore[invalid-argument-type]

            if not values:
                return json.dumps(
                    {
                        "thread_id": thread_id,
                        "status": "empty",
                        "message": "No conversation found for this thread",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

            state = values.get("values", {})
            messages = state.get("messages", [])
            summary = state.get("summarized_history", "")

            return json.dumps(
                {
                    "thread_id": thread_id,
                    "status": "active",
                    "message_count": len(messages),
                    "summary": summary or f"Thread with {len(messages)} messages",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

    except Exception:
        logger.exception("Failed to get thread context: %s", thread_id)
        return json.dumps(
            {"thread_id": thread_id, "status": "error", "error": "Context unavailable"}
        )


@mcp.resource("vectora://thread/{thread_id}/history")
async def get_thread_history(thread_id: str) -> str:
    """Returns the recent message history of a Vectora conversation thread.

    Useful for understanding recent conversation context before calling tools.

    Args:
        thread_id: Thread/conversation ID

    Returns:
        JSON string with last 5 messages
    """
    logger.info("Resource: get_thread_history(%s)", thread_id)

    try:
        async with Checkpointer() as checkpointer:
            config = {"configurable": {"thread_id": str(thread_id)}}
            values = await checkpointer.aget(config)  # ty: ignore[invalid-argument-type]

            if not values:
                return json.dumps(
                    {"thread_id": thread_id, "status": "empty", "messages": []}
                )

            state = values.get("values", {})
            messages = state.get("messages", [])
            recent = messages[-5:] if len(messages) > 5 else messages

            return json.dumps(
                {
                    "thread_id": thread_id,
                    "status": "active",
                    "message_count": len(messages),
                    "recent_messages": [
                        {
                            "type": msg.__class__.__name__,
                            "content": str(msg.content)[:500],
                        }
                        for msg in recent
                    ],
                }
            )

    except Exception:
        logger.exception("Failed to get thread history: %s", thread_id)
        return json.dumps(
            {"thread_id": thread_id, "status": "error", "error": "History unavailable"}
        )


@mcp.resource("vectora://status")
async def get_server_status() -> str:
    """Returns the current status and capabilities of the Vectora MCP server.

    Returns:
        JSON string with server status, version, and active features
    """
    logger.info("Resource: get_server_status")

    tools_count = len(mcp._tool_manager.list_tools())
    return json.dumps(
        {
            "server": "Vectora",
            "version": settings.version,
            "status": "ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "capabilities": {
                "mcp_enabled": settings.enable_mcp,
                "embedding_queue_enabled": settings.embedding_queue_enabled,
            },
            "tools_count": tools_count,
            "resources_count": 4,
        }
    )


@mcp.resource("vectora://collections")
async def list_vector_collections() -> str:
    """Returns available vector search collections in LanceDB.

    Useful for understanding what knowledge bases are indexed and ready for search.

    Returns:
        JSON string with list of collections and their status
    """
    logger.info("Resource: list_vector_collections")

    try:
        import lancedb

        if lancedb is None or settings.lancedb_dir is None:
            return json.dumps(
                {"status": "unavailable", "reason": "LanceDB not configured"}
            )

        db = await lancedb.connect_async(str(settings.lancedb_dir))
        table_names = await db.table_names()

        collections = []
        for table_name in table_names:
            try:
                table = await db.open_table(table_name)
                count = await table.count_rows()
                collections.append(
                    {"name": table_name, "documents": count, "status": "ready"}
                )
            except Exception as e:
                logger.warning(f"Error reading collection {table_name}: {e}")
                collections.append(
                    {"name": table_name, "documents": 0, "status": "error"}
                )

        return json.dumps(
            {
                "status": "success",
                "collections_count": len(collections),
                "collections": collections,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    except Exception:
        logger.exception("Failed to list vector collections")
        return json.dumps({"status": "error", "error": "Unable to list collections"})


logger.info("4 resources registered: context, history, status, collections")


# ============================================================================
# SSE HEARTBEAT
# ============================================================================

_SSE_HEARTBEAT_INTERVAL = 25  # segundos — abaixo do timeout típico de 30-60s


def _run_sse_with_heartbeat(mcp_instance: Any, host: str, port: int) -> None:
    """Roda o servidor SSE com heartbeat de 25s injetado no EventSourceResponse.

    Firewalls e load-balancers costumam fechar conexões HTTP idle após 30-60s.
    O SSE usa um único stream HTTP persistente — sem tráfego, a conexão é
    silenciosamente dropada. O parâmetro ``ping`` do sse-starlette envia uma
    linha de comentário SSE (": ping\\n\\n") a cada N segundos, mantendo o
    stream vivo sem modificar o protocolo MCP.

    Estratégia: monkey-patch no ``EventSourceResponse`` do sse-starlette e do
    módulo mcp.server.sse *antes* de criar o Starlette app, para que todas as
    conexões SSE já nasçam com ping habilitado.
    """
    import anyio
    import uvicorn

    try:
        import sse_starlette.sse as _sse_mod
        from sse_starlette.sse import EventSourceResponse as _OrigESR

        class _ESRWithHeartbeat(_OrigESR):
            """EventSourceResponse que força ping=25s em todas as conexões SSE."""

            def __init__(
                self, *args: Any, ping: int | None = None, **kwargs: Any
            ) -> None:
                super().__init__(
                    *args,
                    ping=ping if ping is not None else _SSE_HEARTBEAT_INTERVAL,
                    **kwargs,
                )

        # Substituir em sse_starlette.sse e em mcp.server.sse (já importado)
        _sse_mod.EventSourceResponse = _ESRWithHeartbeat  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
        with contextlib.suppress(Exception):
            import mcp.server.sse as _mcp_sse  # type: ignore[import-untyped]

            _mcp_sse.EventSourceResponse = _ESRWithHeartbeat  # type: ignore[assignment]  # ty: ignore[invalid-assignment]

        logger.info("SSE heartbeat enabled: ping every %ds", _SSE_HEARTBEAT_INTERVAL)
    except ImportError:
        logger.warning("sse-starlette not available — SSE heartbeat disabled")

    async def _serve() -> None:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Mount, Route

        async def _tools_schema_http(request: Request) -> JSONResponse:
            """GET /api/tools/schema — para a Discovery Layer da Web UI (D1.1)."""
            from vectora.nodes.tools import ALL_TOOLS

            tools_data = []
            for t in ALL_TOOLS:
                schema: dict = {}
                try:
                    args_schema = getattr(t, "args_schema", None)
                    if args_schema is not None and hasattr(
                        args_schema, "model_json_schema"
                    ):
                        schema = args_schema.model_json_schema()
                except Exception:
                    pass
                tools_data.append(
                    {
                        "name": t.name,
                        "description": (t.description or "").split("\n")[0][:200],
                        "args_schema": schema,
                        "render_hint": (t.extras or {}).get("render_hint", "json"),
                    }
                )

            return JSONResponse(
                {
                    "version": "1",
                    "tool_count": len(tools_data),
                    "tools": tools_data,
                }
            )

        sse_app = mcp_instance.sse_app()
        # Montar o endpoint HTTP de schema antes do app SSE
        starlette_app = Starlette(
            routes=[
                Route("/api/tools/schema", _tools_schema_http, methods=["GET"]),
                Mount("/", app=sse_app),
            ]
        )

        config = uvicorn.Config(
            starlette_app,
            host=host,
            port=port,
            timeout_keep_alive=120,  # keep-alive HTTP generoso para SSE
            log_level="warning",
        )
        server = uvicorn.Server(config)
        await server.serve()

    anyio.run(_serve)


# ============================================================================
# ENTRY POINT
# ============================================================================


def run() -> None:
    """Start Vectora as MCP server with configurable transport.

    Entry point: vectora-mcp → vectora.mcp.server:run

    Suporta dois modos de transport via env var MCP_TRANSPORT:
    - "stdio" (default): para clientes locais (Claude Desktop, Claude Code)
    - "sse": para múltiplos agentes remotos via HTTP/SSE (Paperclip, etc.)

    Em modo stdio:
        Lê/escreve JSON-RPC via stdin/stdout. Logs vão para arquivo.
        Status feedback via stderr (não interfere com protocolo).

    Em modo sse:
        Escuta em MCP_HOST:MCP_PORT (default: 0.0.0.0:8000).
        Múltiplos agentes podem conectar simultaneamente via HTTP.
        Cada agente passa seu próprio thread_id para isolamento de sessão.
    """
    import os

    from rich.console import Console
    from rich.panel import Panel

    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    host = os.getenv("MCP_HOST", "0.0.0.0")  # noqa: S104  # nosec B104
    port = int(os.getenv("MCP_PORT", "8000"))

    # stderr é seguro — em stdio, stdout é reservado ao JSON-RPC
    err_console = Console(stderr=True)

    if transport == "sse":
        err_console.print(
            Panel(
                "[bold green]✓ Vectora MCP Server pronto (Multi-Agent)[/bold green]\n"
                f"[dim]Transport:[/dim] SSE HTTP  [dim]Endpoint:[/dim] http://{host}:{port}/sse\n"
                "[dim]Tools:[/dim] 14  [dim]Resources:[/dim] 4\n"
                f"[dim]Logs:[/dim] {_log_dir / 'mcp.log'}\n"
                "[yellow]⚡ Múltiplos agentes podem conectar simultaneamente[/yellow]",
                title="[bold cyan]Vectora MCP (Multi-Agent Hub)[/bold cyan]",
                border_style="cyan",
            )
        )
        logger.info(
            "Starting Vectora MCP server",
            extra={"transport": "sse", "host": host, "port": port},
        )
    else:
        err_console.print(
            Panel(
                "[bold green]✓ Vectora MCP Server pronto[/bold green]\n"
                "[dim]Transport:[/dim] stdio JSON-RPC  "
                "[dim]Tools:[/dim] 14  [dim]Resources:[/dim] 4\n"
                f"[dim]Logs:[/dim] {_log_dir / 'mcp.log'}",
                title="[bold cyan]Vectora MCP[/bold cyan]",
                border_style="cyan",
            )
        )
        logger.info("Starting Vectora MCP server", extra={"transport": "stdio"})

    logger.info("Tools: 14 | Resources: 4")

    try:
        if transport == "sse":
            # FastMCP SSE: HTTP transport para múltiplos agentes remotos.
            # Configura host/port e injeta heartbeat de 25s para evitar que
            # firewalls fechem conexões SSE idle após 30-60s.
            mcp.settings.host = host
            mcp.settings.port = port
            _run_sse_with_heartbeat(mcp, host, port)
        else:
            # stdio JSON-RPC (default) — Claude Desktop, Claude Code
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Vectora MCP server stopped by user")
        sys.exit(0)
    except Exception:
        logger.exception("Fatal error in Vectora MCP server")
        sys.exit(1)


if __name__ == "__main__":
    run()
