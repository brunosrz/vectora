"""Supervisor — Classifica a intenção do usuário e roteia para o agent correto.

Rota de saída:
  "search"      → Search Agent (busca web + RAG)
  "coder"       → Coder Agent (filesystem, terminal, git)
  "direct"      → Direct Agent (resposta direta, síntese)
  "rag_subgraph"→ RAG pipeline (retrieve → rerank → inject → direct)
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langgraph.types import Command

if TYPE_CHECKING:
    from vectora.state import State

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Padrões de classificação
# ---------------------------------------------------------------------------

_INGEST_PATTERNS = re.compile(
    r"\b("
    r"embed(ding)?|indexa(r)?|ingeri(r)?|ingestão|ingest"
    r"|rag add|adiciona(r)? (ao|no|na) rag"
    r")\b",
    re.IGNORECASE,
)

_DIRECT_PATTERNS = re.compile(
    r"^("
    r"oi|olá|ola|hey|hi|hello|tudo bem|tudo bom|como vai|bom dia|boa tarde|boa noite"
    r"|obrigad[oa]|valeu|ok|okay|certo|entendido|perfeito|ótimo|legal|show"
    r"|quem (é você|es você|você é)|o que (você é|você faz|é o vectora)"
    r"|me apresente|apresentação|sobre você"
    r"|thanks|thank you|got it|understood|great|nice|cool"
    r"|who are you|what are you|what can you do"
    r")[!?.,]*$",
    re.IGNORECASE,
)

# Mensagens de identidade pessoal — sempre responder diretamente do system prompt,
# NUNCA via RAG ou web search (evita hallucination de identidade).
_IDENTITY_PATTERNS = re.compile(
    r"\b("
    r"meu nome (é|e)|me chamo|sou o|sou a"
    r"|lembra de mim|você me conhece|me conhece|você lembra"
    r"|sou (o |a )?(criador|dono|owner|developer|desenvolvedor|autor|autor)"
    r"|my name is|i am the (creator|owner|developer|author)"
    r"|i('m| am) bruno|eu sou o bruno|me reconhece"
    r")\b",
    re.IGNORECASE,
)

# URLs explícitas — usar fetch_url, não vector_search
_URL_PATTERNS = re.compile(
    r"https?://\S+",
    re.IGNORECASE,
)

# Caminhos de arquivo locais (Windows e Unix) — usar ferramentas de filesystem
_FILE_PATH_PATTERNS = re.compile(
    r"(?:"
    r"[A-Za-z]:\\[\w\\\-\. ]+"  # Windows: C:\Users\...
    r"|/(?:home|Users|tmp|var|etc|opt|root)/[\w/\-\.]+"  # Unix absoluto
    r"|~/[\w/\-\.]+"  # Unix ~/ relativo
    r")\.\w{1,10}",  # extensão obrigatória: .py, .md, .txt, etc.
    re.IGNORECASE,
)

_CODER_PATTERNS = re.compile(
    r"\b("
    r"cria(r)?|escreve(r)?|edita(r)?|salva(r)?|apaga(r)?|deleta(r)?|move(r)?"
    r"|arquivo|pasta|diretório|directório|código|script|função|classe|módulo"
    r"|terminal|comando|executa(r)?|roda(r)?|instala(r)?|compila(r)?|build"
    r"|git|npm|pip|uv|docker|make|pytest|uvicorn|poetry"
    r"|file|folder|directory|code|function|class|module|run|execute|install|compile"
    r"|create file|write file|edit file|delete file|read file"
    r")\b",
    re.IGNORECASE,
)

_SEARCH_PATTERNS = re.compile(
    r"\b("
    r"busca(r)? na web|pesquisa(r)? na internet|procura(r)? online"
    r"|search|google|notícia(s)?|news|atualidade(s)?"
    r"|o que (aconteceu|está acontecendo)|quem (foi|inventou)"
    r"|quando (foi|aconteceu)|onde (fica|está)"
    r"|acessa(r)? url|abre(r)? link|fetch url|download page"
    r"|search the web|look up|find out|what is|who is|when did|where is"
    r")\b",
    re.IGNORECASE,
)

_RAG_PATTERNS = re.compile(
    r"\b("
    r"documento(s)?|doc(s)?|wiki|base de conhecimento|knowledge base"
    r"|indexad[oa]|embeddings?|lancedb"
    r"|o que (diz|está escrito|consta)|segundo o(s)? documento(s)?"
    r"|com base no(s)?|de acordo com|conforme o(s)?"
    r"|na documenta(ção|cao)|no manual|no guia|no relat(ório|orio)|no projeto"
    r"|document(s)?|indexed|knowledge base|according to|based on"
    r"|in the docs|in the manual|in the guide|in the report"
    r")\b",
    re.IGNORECASE,
)


def classify_intent(text: str) -> str:
    """Classifica intenção da mensagem em: direct | coder | search | rag.

    Prioridade (ordem estrita):
      1. direct   — saudações e meta-perguntas curtas (regex exata)
      2. identity — mensagens de identidade pessoal → direct (NUNCA via RAG/web)
      3. url      — URL explícita (http/https) → search (fetch_url)
      4. filepath — caminho de arquivo local → coder (filesystem tools)
      5. ingest   — embedding/indexação de pastas → search
      6. coder    — filesystem, terminal, código, git
      7. search   — busca web explícita
      8. rag      — consulta a documentação / base indexada
      9. direct   — fallback padrão (conversas, perguntas gerais, contexto)

    Nota: RAG NÃO é fallback universal. Use apenas quando há indício claro de
    consulta a documentação indexada. Para tudo mais, direct é o fallback seguro.
    Todos os agentes têm acesso a ALL_TOOLS — o routing é especialidade, não restrição.
    """
    stripped = text.strip()

    # 1. Saudações e meta-perguntas curtas
    if _DIRECT_PATTERNS.match(stripped):
        return "direct"

    # 2. Identidade pessoal — SEMPRE direto, nunca RAG ou web search
    if _IDENTITY_PATTERNS.search(stripped):
        return "direct"

    # 3. URL explícita → search agent usa fetch_url
    if _URL_PATTERNS.search(stripped):
        return "search"

    # 4. Caminho de arquivo local → coder usa file_read/file_edit
    if _FILE_PATH_PATTERNS.search(stripped):
        return "coder"

    # 5. Ingestão/embedding de pastas
    if _INGEST_PATTERNS.search(stripped):
        return "search"

    # 6. Operações de código e filesystem
    if _CODER_PATTERNS.search(stripped):
        return "coder"

    # 7. Busca web explícita
    if _SEARCH_PATTERNS.search(stripped):
        return "search"

    # 8. Consulta a documentação indexada (palavras-chave RAG específicas)
    if _RAG_PATTERNS.search(stripped):
        return "rag"

    # 9. Fallback: direct — conversas, perguntas gerais, contexto, síntese
    #    (RAG não deve ser fallback universal — evita buscas vetoriais desnecessárias
    #    e contaminação da base com dados irrelevantes)
    return "direct"


_AGENT_MAP = {
    "direct": "direct",
    "coder": "coder",
    "search": "search",
    "rag": "rag_subgraph",
}


async def supervisor(state: State) -> Command:
    """Nó supervisor: classifica a intenção e roteia para o worker correto.

    Returns:
        Command com goto = worker alvo e routing_decision atualizado no State.
    """
    from vectora.services.tracer import tracer

    messages = state.get("messages", [])
    import contextlib

    session_id: int | None = None
    with contextlib.suppress(Exception):
        session_id = state.get("session_metadata", {}).get("thread_id")  # type: ignore[assignment]

    last_human_text = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_text = str(msg.content)
            break

    intent = classify_intent(last_human_text)
    agent = _AGENT_MAP[intent]

    logger.info(
        "Supervisor: '%s...' → %s (%s)",
        last_human_text[:60],
        agent,
        intent,
    )

    try:
        async with tracer.span("supervisor", "route", session_id=session_id) as s:
            s.set(routing=agent, intent=intent, query_len=len(last_human_text))
    except Exception:
        pass  # tracer nunca quebra o fluxo

    return Command(
        goto=agent,
        update={"routing_decision": intent},  # type: ignore[arg-type]
    )
