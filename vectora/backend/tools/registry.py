"""Tool registry nativo — substitui ``@tool`` de ``langchain.tools``,
``langchain_core.tools.BaseTool`` e ``langchain_core.utils.
function_calling.convert_to_openai_tool``.

Usa Pydantic (``pydantic.create_model`` — já dependência do projeto, não
LangChain-family) pra gerar o JSON Schema de cada tool a partir da
assinatura da função Python, o mesmo papel que ``convert_to_openai_tool``
cumpria antes em cima de ``BaseTool.args_schema``.

Toda tool nativa é ``async def`` (CLAUDE.md regra 10) e recebe
``ctx: ToolContext`` como parâmetro normal — o decorator ``vtool`` filtra
esse parâmetro na hora de gerar o schema (nunca aparece pro LLM), mas o
caller (``backend/engine/conversation_loop.py``) sempre passa ``ctx=``
explicitamente na chamada.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, get_type_hints

from pydantic import BaseModel, create_model

from backend.tools.context import ToolContext

_CTX_PARAM_NAME = "ctx"

_ARGS_SECTION_RE = re.compile(r"^\s*Args:\s*$", re.MULTILINE)
_ARG_LINE_RE = re.compile(r"^\s{4,8}(\w+):\s*(.+)$")


@dataclass(slots=True)
class ToolExtras:
    """Metadados consumidos pela UI/HITL — nunca pela execução do LLM.
    Mesmo shape do ``extras={...}`` que ``@tool(extras=...)`` aceitava."""

    render_hint: str = "default"
    category: str = "general"
    destructive: bool = False
    icon: str = "wrench"
    invalidates: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolSpec:
    """Uma tool registrada — nome, schema gerado, handler async, metadados."""

    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[..., Awaitable[str]]
    extras: ToolExtras
    needs_ctx: bool

    def openai_schema(self) -> dict[str, Any]:
        """JSON Schema no shape ``{"type":"function","function":{...}}`` —
        mesmo formato que os 5 chat clients (``backend/llm/*/chat.py``)
        já consomem hoje via ``convert_to_openai_tool``."""
        params = self.args_model.model_json_schema()
        # Só `title` no nível raiz é removido — providers não esperam esse
        # campo em `parameters`. `$defs` (gerado por Pydantic quando um
        # parâmetro usa um tipo composto/BaseModel aninhado) É mantido de
        # propósito: os `$ref` dentro de `properties` apontam pra lá,
        # removê-lo quebraria o schema. Nenhuma tool de produção usa tipo
        # composto hoje (confirmado — só as tools de teste deste módulo
        # exercitam esse caminho); se uma tool migrada vier a precisar,
        # normalização de strict-mode por provider (ex.
        # `backend/llm/openai/chat_client.py::_normalize_strict_schema`)
        # precisa recursar em `$defs` também, não só em `properties`.
        params.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": params,
            },
        }

    async def ainvoke(self, args: dict[str, Any], ctx: ToolContext) -> str:
        """Chama o handler validando ``args`` contra ``args_model`` primeiro
        — erro de validação vira string de erro tipada, nunca exceção crua
        (CLAUDE.md regra 11)."""
        try:
            validated = self.args_model(**args)
        except Exception as exc:
            return f"Error: argumentos inválidos para '{self.name}': {exc}"
        kwargs = validated.model_dump()
        if self.needs_ctx:
            kwargs[_CTX_PARAM_NAME] = ctx
        try:
            return await self.handler(**kwargs)
        except Exception as exc:
            return f"Error: '{self.name}' falhou: {exc}"


class ToolRegistry:
    """Registro global de ``ToolSpec`` — ``vtool`` popula, o motor nativo e
    a agregação por categoria (``registry_bundles.py``) consultam."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def __contains__(self, name: str) -> bool:
        return name in self._tools


TOOL_REGISTRY = ToolRegistry()


def _parse_arg_descriptions(docstring: str | None) -> dict[str, str]:
    """Extrai descrições por parâmetro da seção ``Args:`` (formato Google,
    já usado em toda a base) — melhora o schema exposto ao LLM, mas nunca
    é obrigatório (schema funciona sem, com descrição vazia por campo)."""
    if not docstring:
        return {}
    match = _ARGS_SECTION_RE.search(docstring)
    if not match:
        return {}
    lines = docstring[match.end() :].splitlines()
    descriptions: dict[str, str] = {}
    for line in lines:
        if line and not line.startswith(" "):
            break
        arg_match = _ARG_LINE_RE.match(line)
        if arg_match:
            descriptions[arg_match.group(1)] = arg_match.group(2).strip()
    return descriptions


def _summary(docstring: str | None) -> str:
    """Primeira linha não vazia da docstring — descrição curta da tool
    (mesmo comportamento que ``@tool`` do LangChain já tinha)."""
    if not docstring:
        return ""
    for line in docstring.strip().splitlines():
        if line.strip():
            return line.strip()
    return ""


def vtool(
    *, extras: ToolExtras | None = None
) -> Callable[[Callable[..., Awaitable[str]]], Callable[..., Awaitable[str]]]:
    """Decorator substituto de ``@tool(extras=...)``. Inspeciona a
    assinatura via ``inspect.signature``/``get_type_hints``, gera um
    ``pydantic.create_model()`` dinâmico ignorando ``ctx: ToolContext``
    (nunca vai pro schema exposto ao LLM), registra no ``TOOL_REGISTRY`` e
    devolve a função original inalterada — chamável diretamente pelos
    testes, como antes."""
    resolved_extras = extras or ToolExtras()

    def decorator(fn: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)
        arg_descriptions = _parse_arg_descriptions(fn.__doc__)

        fields: dict[str, Any] = {}
        needs_ctx = False
        for name, param in sig.parameters.items():
            if name == _CTX_PARAM_NAME:
                needs_ctx = True
                continue
            annotation = hints.get(name, Any)
            if param.default is inspect.Parameter.empty:
                fields[name] = (annotation, ...)
            else:
                fields[name] = (annotation, param.default)

        fn_name: str = fn.__name__  # ty: ignore[unresolved-attribute]
        args_model = create_model(f"{fn_name}Args", **fields)
        if arg_descriptions:
            for field_name, description in arg_descriptions.items():
                if field_name in args_model.model_fields:
                    args_model.model_fields[field_name].description = description
            args_model.model_rebuild(force=True)

        spec = ToolSpec(
            name=fn_name,
            description=_summary(fn.__doc__),
            args_model=args_model,
            handler=fn,
            extras=resolved_extras,
            needs_ctx=needs_ctx,
        )
        TOOL_REGISTRY.register(spec)
        return fn

    return decorator
