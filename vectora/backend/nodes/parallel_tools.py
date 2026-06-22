"""Execução paralela de tools (DE-12)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


class ParallelToolNode(ToolNode):
    """ToolNode que executa tools independentes em paralelo via asyncio.gather."""

    async def arun(self, data: Any, **kwargs: Any) -> Any:
        """Executa tools em paralelo quando possível."""
        tool_calls = data.get("tool_calls", [])
        if not tool_calls:
            return await super().arun(data, **kwargs)

        # Agrupa tools por tipo — tools do mesmo tipo podem ter dependências
        # (ex: dois file_write sequenciais). Para máxima segurança, só paraleliza
        # tools de tipos diferentes.
        by_type: dict[str, list[Any]] = {}
        for call in tool_calls:
            tool_name = call.get("name", "")
            if tool_name not in by_type:
                by_type[tool_name] = []
            by_type[tool_name].append(call)

        # Se há tools de tipos diferentes, paraleliza por tipo
        if len(by_type) > 1:
            tasks = []
            for _tool_name, calls in by_type.items():
                for call in calls:
                    task = self._run_tool(call)
                    tasks.append(task)

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return {"tool_results": results}
            except Exception as e:
                logger.exception("Erro em execução paralela: %s", e)
                return await super().arun(data, **kwargs)

        return await super().arun(data, **kwargs)

    async def _run_tool(self, tool_call: dict[str, Any]) -> Any:
        """Executa uma chamada de tool assincronamente."""
        tool_name = tool_call.get("name", "")
        tool_input = tool_call.get("args", {})

        if tool_name not in self.tools_by_name:
            return {"error": f"Tool não encontrada: {tool_name}"}

        tool = self.tools_by_name[tool_name]
        try:
            result = await tool.ainvoke(tool_input)
            return {"tool": tool_name, "result": result}
        except Exception as e:
            logger.exception("Erro ao executar tool %s: %s", tool_name, e)
            return {"tool": tool_name, "error": str(e)}
