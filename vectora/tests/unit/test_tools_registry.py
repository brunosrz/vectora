"""``backend/tools/registry.py`` — tool registry nativo (Sprint 14 WS2),
substitui ``@tool``/``BaseTool``/``convert_to_openai_tool`` do LangChain.

Tools de exemplo definidas aqui (não em ``backend/tools/*.py`` de produção)
— migrar as ~152 tools reais fica pro corte de dispatch feito no
Workstream 5 (o loop nativo), quando o mecanismo antigo (deepagents/
LangGraph, que exige ``BaseTool``) é substituído de vez. Registrar as duas
listas de tools em paralelo agora duplicaria toda tool existente sem
necessidade.
"""

from __future__ import annotations

from backend.tools.context import ToolContext
from backend.tools.registry import (
    TOOL_REGISTRY,
    ToolExtras,
    ToolRegistry,
    ToolSpec,
    vtool,
)

_registry_local = ToolRegistry()


def _get(name: str) -> ToolSpec:
    spec = TOOL_REGISTRY.get(name)
    assert spec is not None, f"tool {name!r} não registrada"
    return spec


@vtool(extras=ToolExtras(category="test", destructive=False))
async def _hash_text(text: str, algorithm: str = "sha256") -> str:
    """Hash de string.

    Args:
        text: Texto a ser hasheado
        algorithm: Algoritmo (sha256, md5)
    """
    import hashlib

    h = hashlib.new(algorithm)
    h.update(text.encode())
    return h.hexdigest()


@vtool(extras=ToolExtras(category="test", destructive=True))
async def _write_note(path: str, content: str, ctx: ToolContext) -> str:
    """Escreve uma nota (tool de exemplo que usa ctx).

    Args:
        path: Caminho da nota
        content: Conteúdo a escrever
    """
    return f"escrito em {path} (workspace={ctx.workspace_id}): {content}"


@vtool()
async def _always_fails(x: int) -> str:
    """Tool que sempre levanta, pra testar o guard de exceção."""
    raise RuntimeError("falha proposital")


class TestVtoolSchemaGeneration:
    def test_registra_tool_no_registry_global(self):
        spec = _get("_hash_text")
        assert spec.name == "_hash_text"

    def test_schema_openai_tem_parametros_primitivos_e_defaults(self):
        schema = _get("_hash_text").openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "_hash_text"
        props = schema["function"]["parameters"]["properties"]
        assert "text" in props
        assert "algorithm" in props
        # `text` não tem default -> obrigatório; `algorithm` tem -> opcional.
        required = schema["function"]["parameters"].get("required", [])
        assert "text" in required
        assert "algorithm" not in required

    def test_ctx_nunca_aparece_no_schema_exposto_ao_llm(self):
        """Erro/borda: se `ctx` vazasse pro schema, o LLM tentaria
        preenchê-lo — quebraria toda chamada de tool que usa ToolContext."""
        spec = _get("_write_note")
        schema = spec.openai_schema()
        props = schema["function"]["parameters"]["properties"]

        assert "ctx" not in props
        assert spec.needs_ctx is True

    def test_descricao_por_argumento_extraida_da_docstring(self):
        schema = _get("_hash_text").openai_schema()
        props = schema["function"]["parameters"]["properties"]

        assert props["text"]["description"] == "Texto a ser hasheado"


class TestToolSpecAinvoke:
    async def test_ainvoke_chama_handler_e_devolve_string(self):
        result = await _get("_hash_text").ainvoke({"text": "oi"}, ctx=ToolContext())

        import hashlib

        assert result == hashlib.sha256(b"oi").hexdigest()

    async def test_ainvoke_injeta_ctx_quando_tool_pede(self):
        ctx = ToolContext(workspace_id="ws-1")
        result = await _get("_write_note").ainvoke(
            {"path": "a.md", "content": "x"}, ctx=ctx
        )

        assert "workspace=ws-1" in result

    async def test_ainvoke_com_args_invalidos_devolve_erro_tipado_sem_levantar(self):
        """Erro/borda: argumento de tipo errado (int esperado, string
        chega) nunca deve propagar exceção — vira string de erro pro LLM
        reagir, igual ao contrato de todas as tools do Vectora."""
        result = await _get("_always_fails").ainvoke(
            {"x": "não é um int"}, ctx=ToolContext()
        )

        assert result.startswith("Error:")

    async def test_ainvoke_com_excecao_do_handler_devolve_erro_tipado(self):
        """Erro/borda: handler que levanta (não erro de validação de
        argumento, erro de execução) também nunca propaga."""
        result = await _get("_always_fails").ainvoke({"x": 1}, ctx=ToolContext())

        assert result.startswith("Error:")
        assert "falha proposital" in result


class TestToolRegistryIsolated:
    def test_registry_proprio_nao_interfere_no_global(self):
        """Confirma que uma instância isolada de ToolRegistry (usada por
        quem quiser um subconjunto de tools, ex. um subagente com toolset
        restrito) não polui o TOOL_REGISTRY global nem vice-versa."""
        assert "_hash_text" not in _registry_local
        assert "_hash_text" in TOOL_REGISTRY
