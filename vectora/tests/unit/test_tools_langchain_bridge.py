"""Testes para backend/tools/langchain_bridge.py — ponte ToolSpec nativo
-> StructuredTool do LangChain, usada pra migrar tools pro registry
nativo uma de cada vez, sem exigir big-bang com o corte de dispatch."""

from __future__ import annotations

from backend.tools.context import ToolContext
from backend.tools.langchain_bridge import as_langchain_tool
from backend.tools.registry import TOOL_REGISTRY, ToolExtras, vtool


def _make_bridge_spec(nome: str, handler):
    """Registra `handler` via `@vtool` sob `nome`, devolve o `ToolSpec` e
    remove do TOOL_REGISTRY global logo em seguida (evita colisão de nome
    entre testes, mesmo padrão de test_engine_guardrails.py)."""
    handler.__name__ = nome
    vtool(extras=ToolExtras(category="general", destructive=False))(handler)
    spec = TOOL_REGISTRY.get(nome)
    assert spec is not None
    TOOL_REGISTRY._tools.pop(nome, None)
    return spec


class TestAsLangchainTool:
    async def test_happy_path_invoca_via_ainvoke_com_config_injetado(self):
        async def somar(a: int, b: int, ctx: ToolContext) -> str:
            """soma dois números."""
            return str(a + b)

        spec = _make_bridge_spec("ponte_somar", somar)
        lc_tool = as_langchain_tool(spec)

        resultado = await lc_tool.ainvoke(
            {"a": 2, "b": 3}, config={"configurable": {"user_id": "alice"}}
        )

        assert resultado == "5"

    async def test_ctx_e_convertido_do_runnable_config(self):
        capturado: dict[str, str] = {}

        async def ver_usuario(ctx: ToolContext) -> str:
            """devolve o user_id do contexto."""
            capturado["user_id"] = ctx.user_id
            return ctx.user_id

        spec = _make_bridge_spec("ponte_ver_usuario", ver_usuario)
        lc_tool = as_langchain_tool(spec)

        await lc_tool.ainvoke(
            {}, config={"configurable": {"user_id": "bob", "workspace_id": "ws-1"}}
        )

        assert capturado["user_id"] == "bob"

    async def test_sem_config_usa_contexto_padrao(self):
        async def ver_usuario2(ctx: ToolContext) -> str:
            """devolve o user_id do contexto."""
            return ctx.user_id

        spec = _make_bridge_spec("ponte_ver_usuario2", ver_usuario2)
        lc_tool = as_langchain_tool(spec)

        resultado = await lc_tool.ainvoke({})

        assert resultado == "local"

    def test_extras_preservados_no_atributo_extras(self):
        async def qualquer(ctx: ToolContext) -> str:
            """tool qualquer."""
            return "ok"

        qualquer.__name__ = "ponte_extras"
        vtool(
            extras=ToolExtras(
                render_hint="json",
                category="mcp",
                destructive=True,
                icon="share-2",
                invalidates=["threads"],
            )
        )(qualquer)
        spec = TOOL_REGISTRY.get("ponte_extras")
        assert spec is not None
        TOOL_REGISTRY._tools.pop("ponte_extras", None)

        lc_tool = as_langchain_tool(spec)

        assert lc_tool.extras == {
            "render_hint": "json",
            "category": "mcp",
            "destructive": True,
            "icon": "share-2",
            "invalidates": ["threads"],
        }

    async def test_erro_da_tool_original_propaga_como_string_de_erro(self):
        async def falha(ctx: ToolContext) -> str:
            """tool que sempre falha."""
            return "Error: algo deu errado"

        spec = _make_bridge_spec("ponte_falha", falha)
        lc_tool = as_langchain_tool(spec)

        resultado = await lc_tool.ainvoke({})

        assert resultado == "Error: algo deu errado"
