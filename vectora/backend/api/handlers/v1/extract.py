"""Endpoint de extração estruturada — POST /v1/extract.

Recebe texto livre + JSON Schema e retorna os dados extraídos no formato
solicitado. Usa ``create_deep_agent(response_format=schema)`` com detecção
automática de estratégia (ProviderStrategy quando o modelo suporta,
ToolStrategy como fallback).

Exemplo de request:
    POST /v1/extract
    {
        "text": "João Silva, 32 anos, engenheiro de software em São Paulo",
        "schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string"},
                "idade": {"type": "integer"},
                "cargo": {"type": "string"},
                "cidade": {"type": "string"}
            },
            "required": ["nome"]
        }
    }

Resposta:
    {"nome": "João Silva", "idade": 32, "cargo": "engenheiro de software", "cidade": "São Paulo"}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas de request/response
# ---------------------------------------------------------------------------


class ExtractRequest(BaseModel):
    """Payload para extração estruturada de texto."""

    text: str = Field(..., description="Texto livre para extração.")
    schema_: dict[str, Any] = Field(
        ...,
        alias="schema",
        description="JSON Schema (Draft 7) descrevendo o formato de saída.",
    )
    model_config = {"populate_by_name": True}


class ExtractResponse(BaseModel):
    """Resultado da extração."""

    data: dict[str, Any] = Field(..., description="Dados extraídos conforme o schema.")
    strategy: str = Field(
        default="auto",
        description="Estratégia usada: 'provider' (native) ou 'tool' (tool calling).",
    )


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


@router.post("/v1/extract", response_model=ExtractResponse)
async def extract(request: ExtractRequest, http_request: Request) -> ExtractResponse:
    """Extrai dados estruturados de texto usando o LLM ativo.

    Auto-detecta a estratégia:
    - ``ProviderStrategy``: usa structured output nativo do provider (Anthropic, OpenAI, Gemini)
    - ``ToolStrategy``: fallback via tool calling para provedores sem suporte nativo

    O schema JSON passado no request é convertido em um modelo Pydantic dinamicamente
    para compatibilidade com ``create_deep_agent(response_format=...)``.
    """
    from langchain_core.messages import HumanMessage

    from backend.services.utils import load_llm

    # Converte JSON Schema para Pydantic model dinamicamente
    schema_type = _json_schema_to_pydantic(request.schema_, name="ExtractOutput")

    # Detecção de estratégia: tenta ProviderStrategy primeiro
    strategy_name, response_format = _detect_strategy(schema_type)

    try:
        from typing import cast as _cast

        from deepagents import create_deep_agent
        from langchain_core.language_models.chat_models import BaseChatModel

        llm = _cast("BaseChatModel", load_llm())

        # Cria agente one-shot com structured output
        agent = create_deep_agent(
            llm,
            tools=[],
            system_prompt=(
                "Você é um extrator de informações. "
                "Extraia apenas as informações presentes no texto fornecido. "
                "Se uma informação não estiver no texto, omita o campo ou use null."
            ),
            response_format=response_format,
        )

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=request.text)]},
            config={"configurable": {}},
        )

        # Extrai o dado estruturado do resultado
        output = result.get("structured_response") or result.get("messages", [{}])[-1]
        if hasattr(output, "model_dump"):
            data = output.model_dump(exclude_none=True)
        elif isinstance(output, dict):
            data = output
        else:
            data = {"result": str(output)}

    except Exception as exc:
        logger.exception("extract: falha na extração")
        raise HTTPException(status_code=500, detail=f"Erro na extração: {exc}") from exc

    return ExtractResponse(data=data, strategy=strategy_name)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _json_schema_to_pydantic(
    schema: dict[str, Any], name: str = "DynamicModel"
) -> type:
    """Converte um JSON Schema dict em um modelo Pydantic dinâmico.

    Suporte básico: propriedades string/integer/number/boolean/array.
    Tipos complexos (oneOf, anyOf) são mapeados para ``Any``.
    """
    from pydantic import create_model

    _type_map: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])

    fields: dict[str, Any] = {}
    for field_name, field_schema in properties.items():
        py_type = _type_map.get(field_schema.get("type", "string"), Any)
        if field_name in required:
            fields[field_name] = (py_type, ...)
        else:
            fields[field_name] = (py_type | None, None)

    return create_model(name, **fields)


def _detect_strategy(schema_type: type) -> tuple[str, Any]:
    """Detecta e retorna a melhor estratégia de structured output.

    Tenta ``AutoStrategy`` que escolhe automaticamente entre ProviderStrategy
    e ToolStrategy baseado no modelo em uso.
    """
    try:
        from langchain.agents.structured_output import AutoStrategy

        return "auto", AutoStrategy(schema_type)
    except ImportError:
        pass

    # Fallback: passa o tipo diretamente (create_deep_agent detecta)
    return "auto", schema_type
