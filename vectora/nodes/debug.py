"""Debug wrapper — DiagnosticToolNode para logging detalhado de tool_calls."""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt.tool_node import ToolNode

from vectora.state import State

logger = logging.getLogger(__name__)


class DiagnosticToolNode(ToolNode):
    """ToolNode com logging detalhado para diagnosticar perda de ToolMessages."""

    async def ainvoke(
        self,
        input: Any,  # noqa: A002
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Executa tools com logging de entrada e saída."""
        state_input: State = input
        logger.info(
            "[TOOL_NODE] ENTRADA",
            extra={
                "messages_count": len(state_input.get("messages", [])),
                "last_message_type": (
                    type(state_input["messages"][-1]).__name__
                    if state_input.get("messages")
                    else None
                ),
            },
        )

        # Log do AIMessage com tool_calls
        if state_input.get("messages"):
            last_msg = state_input["messages"][-1]
            tool_calls = getattr(last_msg, "tool_calls", None)
            if tool_calls:
                logger.info(
                    "[TOOL_NODE] Detectadas tool_calls",
                    extra={
                        "tool_calls_count": len(tool_calls),
                        "tool_names": [
                            (tc.get("name") if isinstance(tc, dict) else tc.name)
                            for tc in tool_calls
                        ],
                    },
                )
            else:
                logger.info(
                    "[TOOL_NODE] Nenhuma tool_call detectada na última mensagem"
                )

        # Chama ToolNode original
        try:
            result = await super().ainvoke(input, config, **kwargs)

            logger.info(
                "[TOOL_NODE] SAÍDA",
                extra={
                    "result_keys": list(result.keys()) if result else [],
                    "result_type": type(result).__name__ if result else "None",
                    "messages_in_result": (
                        len(result.get("messages", []))
                        if result and isinstance(result, dict) and "messages" in result
                        else 0
                    ),
                },
            )

            # Log de cada ToolMessage retornado
            if result and isinstance(result, dict) and "messages" in result:
                for i, msg in enumerate(result["messages"]):
                    logger.info(
                        f"[TOOL_NODE] ToolMessage[{i}]",
                        extra={
                            "type": type(msg).__name__,
                            "tool_use_id": getattr(msg, "tool_use_id", "N/A"),
                            "content_length": len(str(getattr(msg, "content", ""))),
                        },
                    )
            elif result:
                logger.warning(
                    "[TOOL_NODE] Resultado não é dict ou não tem 'messages'",
                    extra={
                        "result_type": type(result).__name__,
                        "has_messages_key": "messages" in result
                        if isinstance(result, dict)
                        else False,
                    },
                )

            return result

        except Exception as e:
            logger.exception(
                "[TOOL_NODE] ERRO ao executar ferramentas",
                extra={"error": str(e)},
            )
            raise

    def invoke(
        self,
        input: Any,  # noqa: A002
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Sync wrapper para invoke."""
        state_input: State = input
        logger.info(
            "[TOOL_NODE-SYNC] ENTRADA",
            extra={
                "messages_count": len(state_input.get("messages", [])),
                "last_message_type": (
                    type(state_input["messages"][-1]).__name__
                    if state_input.get("messages")
                    else None
                ),
            },
        )

        try:
            result = super().invoke(input, config, **kwargs)

            logger.info(
                "[TOOL_NODE-SYNC] SAÍDA",
                extra={
                    "result_keys": list(result.keys())
                    if isinstance(result, dict)
                    else "N/A",
                    "result_type": type(result).__name__,
                },
            )

            return result

        except Exception as e:
            logger.exception(
                "[TOOL_NODE-SYNC] ERRO ao executar ferramentas",
                extra={"error": str(e)},
            )
            raise
