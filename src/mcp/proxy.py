"""VectoraProxy: Client helper para múltiplos agentes acessarem o Vectora via MCP.

Permite que sistemas externos (Paperclip, outros agentes) deleguem tarefas para o
Vectora compartilhado, mantendo isolamento de sessão via thread_id.

Arquitetura Multi-Agent:
    - 1 Vectora Server (Docker, singleton AgentManager, LanceDB compartilhado)
    - N Agentes Cliente (cada um com seu próprio thread_id)
    - Sessões isoladas no mesmo SQLite (LangGraph Checkpointer pattern)
    - Transport: stdio (local) ou SSE/HTTP (remoto)

Uso:
    # Modo stdio (local)
    proxy = VectoraProxy(transport="stdio", command="vectora", args=["mcp-server"])

    # Modo SSE (remoto, multi-agent)
    proxy = VectoraProxy(transport="sse", url="http://vectora:8000/sse")

    async with proxy:
        # Cada agente passa seu próprio thread_id
        result = await proxy.delegate(
            task="Analise meu código Python",
            thread_id="paperclip_agent_abc_42"
        )

        # Chamadas a ferramentas individuais
        docs = await proxy.call_tool(
            "vector_search_tool",
            {"query": "RAG patterns", "collection": "docs"}
        )

        # Ler contexto da sessão
        context = await proxy.get_resource(
            f"vectora://thread/{thread_id}/context"
        )
"""

from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Literal, Self

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)


class VectoraProxyError(Exception):
    """Erro genérico do VectoraProxy."""


class VectoraProxy:
    """Cliente proxy para o Vectora MCP Server.

    Encapsula MCPClient para fornecer API ergonômica aos agentes externos.
    Suporta transports stdio (local) e SSE (remoto).

    Attributes:
        transport: Tipo de transport ("stdio" ou "sse")
        url: URL do servidor SSE (somente modo "sse")
        command: Comando para iniciar servidor stdio (somente modo "stdio")
        args: Argumentos do comando stdio
        timeout: Timeout padrão por chamada (segundos)
    """

    def __init__(
        self,
        transport: Literal["stdio", "sse"] = "stdio",
        url: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 300.0,
    ) -> None:
        """Inicializa o VectoraProxy.

        Args:
            transport: "stdio" para servidor local, "sse" para servidor HTTP remoto
            url: URL do endpoint SSE (ex: "http://vectora:8000/sse")
            command: Comando para iniciar servidor stdio (ex: "uv")
            args: Argumentos do comando (ex: ["run", "vectora-mcp"])
            env: Variáveis de ambiente para o servidor stdio
            timeout: Timeout padrão (5 minutos por default)

        Raises:
            ValueError: Se configuração de transport for inválida
        """
        if transport == "sse" and not url:
            raise ValueError("url é obrigatório quando transport='sse'")
        if transport == "stdio" and not command:
            raise ValueError("command é obrigatório quando transport='stdio'")

        self.transport = transport
        self.url = url
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.timeout = timeout

        self._session: Any = None
        self._exit_stack: AsyncExitStack | None = None

    async def __aenter__(self) -> Self:
        """Entra no context async — abre conexão MCP."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Sai do context async — fecha conexão MCP."""
        await self.disconnect()

    async def connect(self) -> None:
        """Estabelece conexão com o servidor MCP.

        Raises:
            VectoraProxyError: Se falhar ao conectar
        """
        try:
            from mcp.client.stdio import stdio_client

            from mcp import ClientSession, StdioServerParameters

            self._exit_stack = AsyncExitStack()

            if self.transport == "sse":
                from mcp.client.sse import sse_client

                if self.url is None:
                    msg = "url required for SSE transport"
                    raise VectoraProxyError(msg)
                read, write = await self._exit_stack.enter_async_context(
                    sse_client(url=self.url)
                )
            else:
                # stdio
                if self.command is None:
                    msg = "command required for stdio transport"
                    raise VectoraProxyError(msg)
                server_params = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    env=self.env,
                )
                read, write = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )

            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self._session.initialize()

            logger.info(
                "VectoraProxy connected",
                extra={"transport": self.transport, "url": self.url},
            )

        except Exception as e:
            await self.disconnect()
            raise VectoraProxyError(f"Falha ao conectar ao Vectora: {e}") from e

    async def disconnect(self) -> None:
        """Fecha conexão com o servidor MCP."""
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Erro ao desconectar: {e}")
            finally:
                self._exit_stack = None
                self._session = None
                logger.info("VectoraProxy disconnected")

    async def delegate(
        self,
        task: str,
        thread_id: str | int = 1,
    ) -> str:
        """Delega uma tarefa complexa para o Vectora (A2A pattern).

        O Vectora executa seu LangGraph interno completo:
        - Decision-making sobre ferramentas
        - RAG, web search, file ops, terminal
        - Reasoning e síntese
        - Retorna resultado final

        Args:
            task: Descrição da tarefa em linguagem natural
            thread_id: ID único da sessão do agente cliente
                       (cada agente Paperclip deve usar seu próprio ID)

        Returns:
            Resultado final processado pelo Vectora

        Raises:
            VectoraProxyError: Se a delegação falhar
        """
        if not self._session:
            raise VectoraProxyError("Proxy não conectado. Use 'async with proxy:'")

        try:
            result = await self._session.call_tool(
                "delegate_task_to_vectora",
                arguments={
                    "task_prompt": task,
                    "thread_id": str(thread_id),
                },
            )
            # Extract text from MCP CallToolResult
            return self._extract_text(result)

        except Exception as e:
            logger.exception(
                "Delegation failed",
                extra={"thread_id": thread_id, "task_length": len(task)},
            )
            raise VectoraProxyError(f"Falha na delegação: {e}") from e

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> str:
        """Chama uma ferramenta MCP individual do Vectora.

        Use quando souber exatamente qual ferramenta invocar (não precisa de A2A).
        Mais rápido que delegate() pois não roda LangGraph inteiro.

        Args:
            tool_name: Nome da ferramenta (ex: "vector_search_tool")
            arguments: Argumentos da ferramenta

        Returns:
            Resultado da ferramenta como string

        Raises:
            VectoraProxyError: Se a chamada falhar
        """
        if not self._session:
            raise VectoraProxyError("Proxy não conectado. Use 'async with proxy:'")

        try:
            result = await self._session.call_tool(tool_name, arguments=arguments or {})
            return self._extract_text(result)

        except Exception as e:
            logger.exception(
                "Tool call failed",
                extra={"tool": tool_name, "tool_args": arguments},
            )
            raise VectoraProxyError(f"Falha na ferramenta '{tool_name}': {e}") from e

    async def get_resource(self, resource_uri: str) -> str:
        """Lê um resource do servidor Vectora.

        Resources expõem estado cognitivo do Vectora:
        - vectora://thread/{id}/context: contexto/sumário da conversa
        - vectora://thread/{id}/history: últimas 5 mensagens
        - vectora://status: status e capacidades do servidor
        - vectora://collections: coleções vetoriais disponíveis

        Args:
            resource_uri: URI do resource

        Returns:
            Conteúdo do resource (JSON string)

        Raises:
            VectoraProxyError: Se a leitura falhar
        """
        if not self._session:
            raise VectoraProxyError("Proxy não conectado. Use 'async with proxy:'")

        try:
            result = await self._session.read_resource(resource_uri)
            # Resource result has 'contents' list with 'text' field
            if hasattr(result, "contents") and result.contents:
                return str(result.contents[0].text)
            return str(result)

        except Exception as e:
            logger.exception("Resource read failed", extra={"uri": resource_uri})
            raise VectoraProxyError(
                f"Falha ao ler resource '{resource_uri}': {e}"
            ) from e

    async def list_tools(self) -> list[dict[str, Any]]:
        """Lista todas as ferramentas disponíveis no Vectora.

        Returns:
            Lista de tools com nome, descrição e schema
        """
        if not self._session:
            raise VectoraProxyError("Proxy não conectado. Use 'async with proxy:'")

        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in result.tools
        ]

    async def get_thread_context(self, thread_id: str | int) -> dict[str, Any]:
        """Obtém contexto/sumário da thread/sessão de um agente.

        Args:
            thread_id: ID da sessão do agente

        Returns:
            Dict com message_count, summary, status, timestamp
        """
        result = await self.get_resource(f"vectora://thread/{thread_id}/context")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}

    async def get_thread_history(self, thread_id: str | int) -> dict[str, Any]:
        """Obtém histórico recente de mensagens da sessão.

        Args:
            thread_id: ID da sessão do agente

        Returns:
            Dict com recent_messages, message_count, status
        """
        result = await self.get_resource(f"vectora://thread/{thread_id}/history")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}

    @staticmethod
    def _extract_text(call_result: Any) -> str:
        """Extrai texto do CallToolResult do MCP."""
        if hasattr(call_result, "content") and call_result.content:
            # content é uma lista de TextContent
            parts = []
            for item in call_result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(call_result)


# ============================================================================
# FACTORY HELPERS — Conveniência para criar proxies pré-configurados
# ============================================================================


def create_local_proxy(timeout: float = 300.0) -> VectoraProxy:
    """Cria um proxy para servidor Vectora local via stdio.

    Equivalente a executar `vectora mcp-server` localmente.

    Args:
        timeout: Timeout padrão por chamada

    Returns:
        VectoraProxy configurado para stdio
    """
    return VectoraProxy(
        transport="stdio",
        command="vectora",
        args=["mcp-server"],
        timeout=timeout,
    )


def create_remote_proxy(
    url: str = "http://localhost:8000/sse",
    timeout: float = 300.0,
) -> VectoraProxy:
    """Cria um proxy para servidor Vectora remoto via SSE/HTTP.

    Ideal para arquitetura multi-agent onde vários agentes (Paperclip)
    se conectam ao mesmo Vectora rodando em Docker.

    Args:
        url: URL do endpoint SSE
        timeout: Timeout padrão por chamada

    Returns:
        VectoraProxy configurado para SSE
    """
    return VectoraProxy(transport="sse", url=url, timeout=timeout)
