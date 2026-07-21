"""Remember — learning loop: destila um transcript de thread em skills
reutilizáveis e fatos duráveis sobre o usuário, via LLM com saída
estruturada. Nada aqui persiste em disco/BaseStore — só produz o
`DistillationResult` que o caller (tool `learn_from_session`) devolve ao
agente, que por sua vez pede aprovação HITL antes de gravar qualquer coisa
(`install_learned_skill`, `save_memory`).
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_DISTILL_SYSTEM_PROMPT = (
    "Você analisa o transcript de uma conversa entre um usuário e um "
    "agente de IA e extrai APENAS o que vale a pena lembrar para sessões "
    "futuras:\n\n"
    "1. Skills reutilizáveis: padrões de solução que se repetiriam em "
    "outras tarefas semelhantes (ex.: um procedimento de debug, um "
    "template de configuração). Cada skill precisa de um nome curto, uma "
    "descrição de quando usá-la, e o conteúdo (passo a passo) em "
    "Markdown.\n"
    "2. Fatos duráveis sobre o usuário ou o projeto: preferências, "
    "convenções, contexto que não muda a cada sessão.\n\n"
    "Se o transcript não tiver nenhum padrão reutilizável ou fato "
    "durável, devolva listas vazias — isso é um resultado válido, não "
    "uma falha. Nunca invente uma skill genérica só para preencher a "
    "lista."
)


class SkillDraft(BaseModel):
    name: str
    description: str
    content: str


class DistillationResult(BaseModel):
    skills: list[SkillDraft] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)


async def distill_transcript(transcript_text: str) -> DistillationResult:
    """Extrai skills/fatos do `transcript_text` via LLM estruturado.

    Defensivo: transcript vazio ou falha do LLM (rede, parse, timeout)
    devolve `DistillationResult()` vazio — nunca propaga exceção pro
    caller (tool `learn_from_session`)."""
    if not transcript_text.strip():
        return DistillationResult()

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from backend.services.utils import load_llm

        llm = load_llm()
        structured = llm.with_structured_output(DistillationResult)
        result = await structured.ainvoke(
            [
                SystemMessage(content=_DISTILL_SYSTEM_PROMPT),
                HumanMessage(content=transcript_text[:20000]),
            ]
        )
        if isinstance(result, DistillationResult):
            return result
        return DistillationResult.model_validate(result)
    except Exception as exc:
        logger.warning("learning: falha ao destilar transcript — %s", exc)
        return DistillationResult()


def dedupe_skill_drafts(
    drafts: list[SkillDraft], existing_names: set[str]
) -> list[SkillDraft]:
    """Remove drafts cujo nome normalizado já existe entre as skills
    instaladas — evita duplicar/pedir aprovação pra algo já aprendido."""
    normalized_existing = {name.strip().lower() for name in existing_names}
    return [
        draft
        for draft in drafts
        if draft.name.strip().lower() not in normalized_existing
    ]
