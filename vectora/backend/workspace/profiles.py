"""Perfis de harness por provider/modelo (HarnessProfile canônicos do Vectora).

Cada perfil ajusta o comportamento do agente para um provider/modelo específico:
    - ``system_prompt_suffix`` — instrução extra appendada ao system prompt base
    - ``excluded_tools``       — tools removidas do toolset deste provider
    - ``extra_middleware``     — middleware adicional aplicado só neste perfil
    - ``general_purpose_subagent`` — configuração do subagent geral (disable em modelos fracos)

Registrado via ``register_harness_profile`` no startup do factory (``_register_profiles()``).
O deepagents seleciona o perfil mais específico por ``provider:model`` ou por ``provider``.

Referência:
    https://docs.langchain.com/oss/deepagents/customization#provider-profiles
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Tools que modelos locais/fracos não devem ter acesso — sem confiança suficiente
#: para operações destrutivas ou APIs externas.
_OLLAMA_EXCLUDED: frozenset[str] = frozenset(
    {
        # Subagent task delegation (pequenos modelos confundem com tool comum)
        "task",
        # Operações de filesystem destrutivas sem supervisão de IA forte
        "file_write",
        # GitHub — requer tokens e entendimento de contexto avançado
        "gh_pr_create",
        "gh_pr_merge",
        "gh_issue_create",
    }
)

#: Tools com schemas muito grandes que causam erros em alguns modelos Gemini
#: (flash, pro-exp) com low context window em modo tool-calling.
_GEMINI_EXCLUDED: frozenset[str] = frozenset(
    {
        # ingest_docs tem schema grande (glob_pattern, collection, opções avançadas)
        # e não é essencial no fluxo principal de chat.
        "ingest_docs",
        # manage_retriever: raramente usado em chat; pode ser habilitado via settings
        "manage_retriever",
    }
)


# ---------------------------------------------------------------------------
# Registro de perfis
# ---------------------------------------------------------------------------


def _register_profiles() -> None:
    """Registra os perfis de harness do Vectora no deepagents.

    Idempotente: registrar o mesmo perfil duas vezes simplesmente sobrescreve.
    """
    try:
        from deepagents import (  # type: ignore[attr-defined]
            GeneralPurposeSubagentProfile,
            HarnessProfile,
            register_harness_profile,
        )
    except ImportError:
        logger.warning("profiles: deepagents não disponível; perfis não registrados")
        return

    # ── Anthropic Claude ──────────────────────────────────────────────────────
    # Prompt caching: o langchain_anthropic cuida automaticamente via
    # cache_control ephemeral em system messages longas. Aqui adicionamos
    # uma suffix que orienta o uso do extended thinking (quando disponível).
    register_harness_profile(
        "anthropic",
        HarnessProfile(
            system_prompt_suffix=(
                "\n\n## Instrução de raciocínio\n"
                "Quando a tarefa for complexa, use extended thinking (se disponível) "
                "para planejar antes de agir. Seja explícito no plano antes de chamar tools."
            ),
        ),
    )
    logger.debug("profiles: perfil Anthropic registrado")

    # ── Google Gemini ─────────────────────────────────────────────────────────
    # Gemini Flash/Pro-Exp têm contexto menor e schemas de tools pesados causam
    # erros de "too many tokens in tool description". Excluímos tools raramente
    # usadas em chat para reduzir o tamanho do contexto de tools.
    register_harness_profile(
        "google_genai",
        HarnessProfile(
            excluded_tools=_GEMINI_EXCLUDED,
            system_prompt_suffix=(
                "\n\n## Nota de capacidade\n"
                "Você está rodando em Google Gemini. "
                "Se precisar indexar documentos ou gerenciar o RAG, avise o usuário "
                "que essas operações estão disponíveis via configuração avançada."
            ),
        ),
    )
    logger.debug("profiles: perfil Google Gemini registrado")

    # ── Ollama (modelos locais) ────────────────────────────────────────────────
    # Modelos locais geralmente têm 7-13B parâmetros e são menos confiáveis em
    # tool-use complexo. Desabilitamos o subagent geral e excluímos tools
    # que exigem raciocínio avançado (delegação, operações GitHub, file_write).
    register_harness_profile(
        "ollama",
        HarnessProfile(
            excluded_tools=_OLLAMA_EXCLUDED,
            # Desabilita o subagent geral automático — modelos locais não
            # gerenciam delegação bem; o orchestrator responde diretamente.
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
            system_prompt_suffix=(
                "\n\n## Nota de capacidade\n"
                "Você está rodando localmente via Ollama. "
                "Prefira respostas diretas a delegações. "
                "Use apenas as tools mais simples (file_read, grep, web_search, terminal)."
            ),
        ),
    )
    logger.debug("profiles: perfil Ollama registrado")

    logger.debug(
        "profiles: 3 perfis de harness registrados (anthropic, google_genai, ollama)"
    )
