"""Orchestrator — Agent generalista que responde diretamente ou delega a sub-agents.

O orchestrator É o agent principal do Vectora. Ele pode:

  1. **Responder diretamente** — saudações, perguntas de conhecimento, síntese,
     identidade, síntese RAG — sem rotear para outro agent (economiza 1 LLM call).

  2. **Delegar com task query** — quando precisa de especialista, cria uma instrução
     clara e concisa para o sub-agent, em vez de apenas passar o histórico bruto.

  3. **Criar artifacts** — quando o usuário pede planos, specs, task lists, guias
     ou outros documentos estruturados, usa a tool create_artifact para salvar em
     ~/.vectora/artifacts/{session_id}/ em vez de responder apenas com texto.

Sub-agents disponíveis para delegação:
  "coder"  → Coder Agent (filesystem, terminal, git, implementação)
  "search" → Search Agent (web search em tempo real, fetch URL)
  "rag"    → RAG Subgraph (busca semântica na base de conhecimento indexada)

Contexto enviado ao LLM:
  - SystemMessage: contexto do projeto (AGENTS.md, CLAUDE.md, GEMINI.md) — primeira vez
  - SystemMessage: prompt de instrução
  - SystemMessage: bloco de contexto (session_id, tool chain, artifacts)
  - Últimas 5 HumanMessages
  - Últimas 2 AIMessages sem tool_calls (respostas finais, não intermediárias)
"""

from __future__ import annotations

import contextlib
import logging
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END
from langgraph.types import Command

from vectora.agents._identity import VECTORA_IDENTITY
from vectora.types import (
    AgentName,
    CoderResult,
    OrchestratorDecision,
    SearchResult,
    SubTask,
)

if TYPE_CHECKING:
    from vectora.state import State

logger = logging.getLogger(__name__)


def _is_llm_quota_error(err: str) -> bool:
    """Retorna True se o erro indica quota/rate-limit do LLM (Gemini, OpenAI…)."""
    err_lower = err.lower()
    return (
        "429" in err
        or "resource_exhausted" in err_lower
        or "too many requests" in err_lower
        or "rate limit" in err_lower
        or "quota" in err_lower
        or "rateLimitExceeded" in err
        or "quota_exceeded" in err_lower
    )


def _classify_quota_error(exc: Exception) -> str:
    """Classifica o tipo de limite atingido: 'rpm', 'rpd' ou 'unknown'.

    O Gemini inclui `retryDelay` apenas para limites por minuto (RPM).
    Limites diários (RPD/quota total) não têm retry_delay — a API retorna
    RESOURCE_EXHAUSTED sem informar quando vai resetar.
    """
    err_str = str(exc).lower()
    # Sinais de cota diária / total esgotada
    if any(
        s in err_str
        for s in (
            "daily",
            "per day",
            "quota exceeded",
            "quota_exceeded",
            "free tier",
            "billing",
        )
    ):
        return "rpd"
    # Se tem retry_delay → é RPM (limite por minuto)
    if _extract_retry_delay(exc) is not None:
        return "rpm"
    # Genérico: sem retry_delay → provavelmente RPD ou desconhecido
    return "unknown"


def _extract_retry_delay(exc: Exception) -> int | None:
    """Tenta extrair o tempo de retry (segundos) do erro 429 do Gemini/Google API.

    A Google API Core inclui `retryDelay` nos detalhes do erro 429 quando o
    limite é por minuto (RPM). Retorna None se não encontrar o campo.
    """
    try:
        # google.api_core.exceptions.ResourceExhausted tem .details()
        details = getattr(exc, "details", None)
        if callable(details):
            details = details()
        if isinstance(details, list):
            for d in details:
                # d pode ser um proto RetryInfo com retry_delay
                rd = getattr(d, "retry_delay", None)
                if rd is not None:
                    return max(1, int(getattr(rd, "seconds", 0)))
        # Fallback: parsear string do erro (ex: "retry_delay { seconds: 30 }")
        import re

        err_str = str(exc)
        m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", err_str)
        if m:
            return int(m.group(1))
        # Header Retry-After em formato numérico
        m = re.search(r"retry.after['\"]?\s*[:=]\s*['\"]?(\d+)", err_str, re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Schema de saída estruturada
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_ORCHESTRATOR_PROMPT = f"""{VECTORA_IDENTITY}

---

## Seu Papel — Orchestrator

Você é o **Orchestrator** do Vectora — o agent principal e único ponto de resposta
ao usuário. Você pode responder diretamente OU delegar a um sub-agent especializado.
Nunca faz as duas coisas ao mesmo tempo.

---

## Quando responder diretamente (action = "respond")

Use `action: "respond"` e preencha `response` com a resposta completa em markdown.

### Formato OBRIGATÓRIO do campo `response`

**Toda** resposta em markdown deve ser envelopada em um bloco com **exatamente seis
acentos graves** (``` `` `` `` ```) e o identificador `markdown`. Isso garante que
blocos de código triplos dentro da resposta (` ``` `) não quebrem a hierarquia de
parsing no cliente.

Padrão exato (copie o número de crases):

``````
``````markdown
# Título da resposta

Texto em markdown aqui.

```python
print("blocos triplos internos funcionam")
```

Mais texto.
``````
``````

Regras:
- Use seis crases (``` `` `` `` ```) no abre e no fecha. Nunca cinco, nunca sete.
- O identificador imediatamente após as seis crases de abertura é sempre `markdown`.
- Não escape crases internas — blocos ``` ``` ``` continuam funcionando dentro.
- Mesmo respostas curtas ("Olá!", "Pronto.") devem ir dentro do envelope —
  consistência > brevidade do envelope.
- Para respostas que NÃO são markdown (ex.: apenas um JSON, apenas um número),
  ainda envolva: o cliente sempre desempacota a camada externa.

Responda diretamente para:
- Saudações, agradecimentos e conversas simples ("oi", "obrigado", "ok")
- Perguntas sobre o que o Vectora é, faz ou pode fazer
- Identidade do criador do Vectora: reconheça Bruno Soares com base no system prompt — sem RAG, sem web search
- Informações pessoais compartilhadas pelo usuário: preencha `save_memories` e confirme brevemente
- Perguntas de conhecimento geral que não precisam de dados externos
- **Síntese RAG**: quando há um bloco `## Contexto Recuperado (RAG)` no histórico,
  sintetize-o e responda diretamente — o pipeline RAG já fez a recuperação
- Qualquer coisa que NÃO precise de filesystem, terminal, busca web ou base de
  conhecimento

### Artifacts — criar documentos estruturados
Quando o usuário pedir um plano, spec, lista de tarefas, overview, guia, diagrama de
arquitetura ou implementação de referência que deve ser **salvo como documento**:
- Use a tool `create_artifact` — não responda apenas com texto
- Tipos válidos: `plan`, `spec`, `task_list`, `overview`, `guide`, `architecture`,
  `implementation`
- Sempre passe o `session_id` disponível no bloco de contexto do sistema
- Após salvar, confirme ao usuário com o caminho do arquivo

### Identidade do criador
O criador e operador do Vectora é **Bruno Soares** (`https://github.com/brunosrz`).
Reconheça-o imediatamente com base neste system prompt — nunca via RAG ou web.

---

## Memória persistente do usuário — campo `save_memories`

O schema da sua resposta contém o campo opcional **`save_memories`** — uma lista de
objetos `{{key, content}}` que o sistema executará automaticamente antes de continuar.

### Quando preencher

Preencha `save_memories` **sempre** que o usuário compartilhar informações pessoais,
independente da `action` escolhida. Não é necessário nenhum turno extra.

Sinais que **obrigatoriamente** disparam um save:
- Nome próprio → key: "nome"
- Idade / data de nascimento → key: "idade"
- Profissão / cargo → key: "cargo" ou key: "profissao"
- Empresa / organização → key: "empresa"
- Projetos mencionados → key: "projeto_NOME" (um por projeto)
- Linguagem / stack preferida → key: "stack_preferida"
- IDE / editor preferido → key: "ide_preferida"
- País / cidade → key: "localizacao"
- Idioma preferido → key: "idioma_preferido"
- Qualquer preferência explícita → key: "preferencia_TEMA"

### Exemplos

Usuário diz: "me chamo Bruno, tenho 21 anos e criei o Vectora"
save_memories deve conter:
  - key="nome"             content="Bruno Soares"
  - key="idade"            content="21 anos"
  - key="projeto_principal" content="Criador do Vectora (https://github.com/brunosrz/vectora)"

Usuário diz: "uso VSCode e prefiro Python"
save_memories deve conter:
  - key="ide_preferida"       content="VSCode"
  - key="linguagem_preferida" content="Python"

### Regras
- **Não peça permissão** para salvar — salve e confirme brevemente na resposta.
- **Uma chave por conceito** — não concatene tudo numa chave só.
- **Conteúdo em frase natural** — não use JSON dentro do content.
- Se a info já foi salva antes, inclua de novo com o valor atualizado (o sistema faz upsert).
- Se o usuário perguntar "o que você sabe sobre mim?" → responda com base em get_memory
  (delegue ao search ou mencione na resposta que não há memórias salvas).

---

## Quando delegar (action = "delegate")

Use `action: "delegate"`, escolha `delegate_to` e preencha `task_query` com uma
instrução clara e autossuficiente para o sub-agent — 1 a 3 frases diretas.

**coder** — Filesystem, terminal, git, implementação de código e indexação de dados.
Delegue quando: criar/editar arquivos, executar comandos, git, npm, pip,
rodar testes, implementar funcionalidades, "implemente", "crie o arquivo", "execute",
**indexar ou embedar arquivos/pastas** ("faça embedding de", "indexa a pasta",
"adicione ao RAG", "ingest_docs", "rag add"). A ferramenta correta para indexar
pastas é `ingest_docs` — só o coder a utiliza. NÃO use rag para pedidos de indexação.

**search** — Busca web em tempo real, fetch de URLs.
Delegue quando: o usuário quer informação atual da internet, menciona uma URL
explícita (https://...), pede para pesquisar algo online.

**rag** — Consulta à base de conhecimento **já indexada** localmente.
Delegue quando: o usuário pergunta sobre documentos EXISTENTES na base, pede busca
semântica, menciona "de acordo com os documentos", "no manual", "na base".
RAG é para CONSULTAR — não para INDEXAR. Pedidos de indexação → coder.

---

## Como escrever task_query

A `task_query` é a instrução que o sub-agent receberá. Escreva como se estivesse
delegando a um colega que não leu a conversa:

- **Certo:** "Crie o arquivo `src/utils/formatDate.ts` com uma função que formata
  datas no formato DD/MM/YYYY. Use TypeScript com export default."
- **Certo:** "Pesquise no site oficial do LangGraph como implementar checkpointing
  com SQLite em Python. URL: https://langchain-ai.github.io/langgraph"
- **Errado:** "O usuário quer criar um arquivo" (vago demais)
- **Errado:** Repetir todo o histórico da conversa

---

## Quando usar execução paralela (action = "parallel")

Use `action: "parallel"` e preencha `parallel_tasks` quando a tarefa se decompõe em
**2 ou mais subtarefas genuinamente independentes** que podem ser executadas ao mesmo
tempo sem depender do resultado uma da outra.

Exemplos válidos:
- "Pesquise sobre X e também verifique o código Y" → search(X) + coder(Y) em paralelo
- "Busque na web sobre A e consulte o RAG sobre B" → search(A) + rag(B) em paralelo

Cada `SubTask` tem:
- `agent`: "coder", "search" ou "rag"
- `task_query`: instrução completa para aquele agent
- `reason`: por que é independente das outras (1 frase)

**Não use parallel se:** as tasks dependem uma da outra, ou se uma única delegação
resolve o problema. Prefira `delegate` quando em dúvida.

---

## Git workflow

Quando o workspace contém um repositório git, prefira fluxos de trabalho seguros:

- **Antes de modificações grandes**: crie uma branch separada — `git_branch create feature-X`
  — para evitar conflitos com a branch principal.
- **Commit messages** seguem sempre Conventional Commits:
  `feat:` / `fix:` / `refactor:` / `docs:` / `test:` / `chore:`
  Nunca use "wip", "update" ou mensagens vagas — escreva sempre o **porquê**.
- **Pull request**: faça push da branch com `git_push`, depois `gh_pr_create`.
- **Issues abertas**: antes de iniciar uma feature nova, verifique com `gh_issue_list`
  se já existe issue aberta para evitar trabalho duplicado.
- **Force push em main/master**: NUNCA faça sem confirmação explícita do usuário.
  Se o usuário não pediu `--force`, não use.
- **Hotfix em produção**: crie branch a partir de main, commit isolado, PR direto.
- **Code review**: use `gh_pr_view` para inspecionar o PR antes de `gh_pr_review`.

Ao delegar tarefas de git ao **coder**, inclua na `task_query` o contexto completo:
branch atual, objetivo e quaisquer restrições (ex: "não force push em main").

---

## Regras absolutas

1. Se o usuário nomear explicitamente um agent ("use o coder", "chame o search"),
   respeite SEMPRE.
2. Pedidos de implementação de código, criação de arquivos ou indexação/embedding
   → **coder**. Se o usuário pediu para criar/editar/salvar um arquivo, ou para
   "fazer embedding", "indexar", "ingest_docs", delegue ao coder — não gere código
   como texto em `response` e não delegue ao rag.
3. Consultas sobre documentos **já indexados** na base → **rag**.
   Se o usuário pergunta "o que diz o documento", "de acordo com o manual" ou similar,
   delegue ao rag. NUNCA delegue ao rag pedidos de indexação/embedding de novos docs.
4. Pedidos de planos, specs, task lists, guias → use `create_artifact`
   (action="respond").
5. Se já há tool chain na sessão (ex: search concluiu), considere isso ao decidir.
6. Correção do RAG: se o usuário fornecer uma fonte autoritativa (repositório
   canônico, doc oficial) que contradiz algo buscado antes na web, delegue ao
   **search** com a instrução de reavaliar e remover do RAG o conteúdo errado.
7. Fallback: se dúvida entre responder e delegar → **responda diretamente**.

Responda apenas com o JSON estruturado. Nenhum texto adicional.
"""

# Prompt da síntese pós-RAG — usado quando o subgrafo RAG já recuperou o
# contexto e o orchestrator precisa apenas redigir a resposta final.
_RAG_SYNTHESIS_PROMPT = """Você é o Vectora. O pipeline de RAG já recuperou o \
contexto abaixo da base de conhecimento indexada. Sua tarefa é responder à \
pergunta do usuário usando ESSE contexto como fonte primária.

Regras:
- Baseie a resposta no contexto recuperado; cite as fontes quando relevante.
- Se o contexto não contém a informação necessária, diga isso honestamente —
  não invente. Sugira indexar a documentação correta ou refinar a pergunta.
- Responda em português, de forma clara e completa, em markdown.
"""

# Prompts de síntese pós sub-agent (B2 — Structured Outputs)
_CODER_SYNTHESIS_PROMPT = """Você é o Vectora. O Coder Agent acabou de executar \
uma tarefa de desenvolvimento. Sua função é redigir a resposta final ao usuário \
com base no resultado estruturado abaixo.

Regras:
- Seja claro e direto sobre o que foi feito.
- Mencione os arquivos alterados se houver (use caminho relativo/nome do arquivo).
- Se testes rodaram, informe o resultado.
- Se houve falha, explique e sugira próximos passos.
- Adapte o idioma ao da conversa. Responda em markdown.
"""

_SEARCH_SYNTHESIS_PROMPT = """Você é o Vectora. O Search Agent acabou de realizar \
uma pesquisa. Sua função é redigir a resposta final ao usuário com base no resultado \
estruturado abaixo.

Regras:
- Apresente as informações encontradas de forma clara e organizada.
- Cite as fontes (URLs ou títulos) quando relevante.
- Indique o nível de confiança da pesquisa se for baixo (< 0.6).
- Adapte o idioma ao da conversa. Responda em markdown.
"""

# C5 — Síntese de resultados paralelos
_PARALLEL_SYNTHESIS_PROMPT = """Você é o Vectora. Múltiplos agentes executaram \
tasks em paralelo. Sua função é integrar os resultados em uma resposta coesa ao usuário.

Regras:
- Apresente as informações de cada agent de forma integrada, não como listas separadas.
- Destaque conexões ou contradições entre os resultados.
- Seja objetivo e claro. Responda em markdown.
- Se algum agent falhou, mencione brevemente e continue com os que sucederam.
"""

# C5 — Prompts base dos agentes para execução paralela (sem tool calls)
_PARALLEL_AGENT_PROMPTS: dict[str, str] = {
    "coder": (
        "Você é um especialista em desenvolvimento de software. "
        "Responda à tarefa abaixo de forma técnica e precisa. "
        "Em modo análise — não execute ferramentas, responda com seu conhecimento."
    ),
    "search": (
        "Você é um especialista em pesquisa e síntese de informação. "
        "Responda à tarefa abaixo com base no seu conhecimento atualizado. "
        "Seja objetivo e cito fontes quando relevante."
    ),
    "rag": (
        "Você é um especialista em análise de documentação técnica. "
        "Responda à tarefa abaixo sintetizando o que sabe sobre o tema. "
        "Indique quando a resposta precisaria de consulta à base de conhecimento."
    ),
}

# ---------------------------------------------------------------------------
# LLM singletons
# ---------------------------------------------------------------------------

_orchestrator_llm = None
_synthesis_llm = None


def _get_orchestrator_llm() -> object:
    global _orchestrator_llm
    if _orchestrator_llm is None:
        from vectora.nodes.tools import ALL_TOOLS
        from vectora.services.utils import load_llm

        _orchestrator_llm = (
            load_llm()
            .bind_tools(ALL_TOOLS)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            .with_structured_output(OrchestratorDecision)
        )
        logger.debug("orchestrator LLM inicializado com structured output + tools")
    return _orchestrator_llm


def _get_synthesis_llm() -> object:
    """LLM plano (sem structured output, sem tools) para síntese pós-RAG.

    Separado do `_get_orchestrator_llm` de propósito: a síntese precisa
    gerar texto livre, não uma `OrchestratorDecision`. Usar o LLM estruturado
    aqui reabriria a porta para re-rotear ao RAG — exatamente o loop que o
    Bloco A6 elimina.
    """
    global _synthesis_llm
    if _synthesis_llm is None:
        from vectora.services.utils import load_llm

        _synthesis_llm = load_llm()
        logger.debug("orchestrator: LLM de síntese pós-RAG inicializado")
    return _synthesis_llm


# ---------------------------------------------------------------------------
# Funções auxiliares de contexto
# ---------------------------------------------------------------------------


def _compress_tool_chain(messages: list) -> str:
    """Extrai e comprime a cadeia de tool calls da conversa."""
    tool_calls: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                name = tc.get("name", "unknown") if isinstance(tc, dict) else str(tc)
                tool_calls.append(name)

    if not tool_calls:
        return ""

    if len(tool_calls) > 10:
        from collections import Counter

        counts = Counter(tool_calls)
        parts = [f"{name} {n}x" if n > 1 else name for name, n in counts.most_common()]
    else:
        parts = []
        for name, group in groupby(tool_calls):
            count = sum(1 for _ in group)
            parts.append(f"{name} {count}x" if count > 1 else name)

    return " > ".join(parts)


def _build_context_block(state: State, session_id: str | None) -> str | None:
    """Monta bloco de contexto comprimido para o orchestrator."""
    all_messages = list(state.get("messages", []))
    lines: list[str] = []

    if session_id:
        lines.append(f"Session ID: {session_id}")

    chain = _compress_tool_chain(all_messages)
    if chain:
        lines.append(f"Tool chain desta sessão: {chain}")

    artifacts = state.get("artifacts") or []
    for a in artifacts[-3:]:
        filename = Path(a["path"]).name if a.get("path") else "?"
        lines.append(f"Artifact gerado: '{a.get('title', '?')}' → {filename}")

    return "\n".join(lines) if lines else None


def _select_context_messages(all_messages: list) -> list:
    """Seleciona as mensagens mais relevantes para o contexto do orchestrator."""
    human_msgs = [m for m in all_messages if isinstance(m, HumanMessage)][-5:]
    ai_msgs = [
        m
        for m in all_messages
        if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None)
    ][-2:]

    selected = {id(m) for m in human_msgs + ai_msgs}
    return [m for m in all_messages if id(m) in selected]


def _load_project_docs() -> str | None:
    """Escaneia cwd recursivamente por AGENTS.md, CLAUDE.md, GEMINI.md.

    Retorna conteúdo concatenado com cabeçalho por arquivo, ou None se não
    encontrar nada.
    Limita cada arquivo a 4000 chars para não inflar o contexto.
    """
    targets = ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]
    cwd = Path.cwd()
    sections: list[str] = []

    for name in targets:
        for found in sorted(cwd.rglob(name)):
            try:
                text = found.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    rel = found.relative_to(cwd)
                    sections.append(f"## {name} ({rel})\n\n{text[:4000]}")
            except Exception:
                pass

    return "\n\n---\n\n".join(sections) if sections else None


def _load_session_context(workspace_id: str | None = None) -> str | None:
    """Carrega contexto completo da sessão: arquivos de projeto + manifest do workspace.

    Seções (B7):
    1. AGENTS.md / CLAUDE.md / GEMINI.md — instrução do projeto (como antes)
    2. MANIFEST.md do workspace ativo — base de conhecimento indexada

    O manifest é truncado a ~3200 chars para não inflar o contexto. Detalhes
    por bucket ficam disponíveis via `bucket_summary` (tool sob demanda).
    """
    parts: list[str] = []

    # Seção 1: arquivos de instrução do projeto
    project_docs = _load_project_docs()
    if project_docs:
        parts.append(project_docs)

    # Seção 2: manifest do workspace ativo
    if workspace_id:
        try:
            from vectora.services.workspace import workspace_registry

            ws = workspace_registry.get(workspace_id)
            if ws is not None:
                manifest_path = ws.manifest_path()
                if manifest_path.exists():
                    manifest = manifest_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).strip()
                    # Remove frontmatter YAML se presente (--- ... ---)
                    if manifest.startswith("---"):
                        end = manifest.find("---", 3)
                        if end != -1:
                            manifest = manifest[end + 3 :].strip()
                    # Trunca a ~3200 chars (~800 tokens) para economizar contexto
                    if len(manifest) > 3200:
                        manifest = manifest[:3200] + "\n\n[... manifest truncado ...]"
                    workspace_block = (
                        f"## Workspace Ativo: {ws.name} ({ws.id})\n\n"
                        f"{manifest}\n\n"
                        "Ferramentas disponíveis para este workspace:\n"
                        "- `vector_search` — busca semântica filtrada para este workspace\n"
                        "- `workspace_describe`, `bucket_summary` — detalhes do manifest\n"
                        "- `get_memory` — memórias episódicas (consulte quando perguntarem "
                        "sobre preferências ou decisões anteriores)"
                    )
                    parts.append(workspace_block)
        except Exception:
            logger.debug(
                "Falha ao carregar manifest do workspace %s",
                workspace_id,
                exc_info=True,
            )

    return "\n\n---\n\n".join(parts) if parts else None


# Alias para compatibilidade com código existente que importa _load_project_context
_load_project_context = _load_project_docs


# ---------------------------------------------------------------------------
# Mapeamento de nomes
# ---------------------------------------------------------------------------

_AGENT_MAP = {
    "coder": "coder",
    "search": "search",
    "rag": "rag_subgraph",
}


def _is_post_rag(all_messages: list) -> bool:
    """True se a última mensagem é o marcador `rag_context` do subgrafo RAG.

    É o sinal determinístico de que o turno atual já passou pelo pipeline
    RAG. `rag_inject` sempre emite esse `SystemMessage` (mesmo sem docs),
    então a detecção é confiável.
    """
    if not all_messages:
        return False
    last = all_messages[-1]
    return (
        isinstance(last, SystemMessage) and getattr(last, "name", "") == "rag_context"
    )


async def _synthesize_after_rag(
    all_messages: list,
    session_id: str | None,
    state_update_extra: dict,
) -> Command:
    """Síntese pós-RAG: o subgrafo RAG já recuperou o contexto; aqui o
    orchestrator apenas redige a resposta final e encerra o turno.

    Este caminho vai SEMPRE para `END` com um LLM plano — nunca toma decisão
    de roteamento. Isso elimina estruturalmente o loop orchestrator ↔
    rag_subgraph: é impossível re-rotear para o RAG a partir daqui.
    """
    from vectora.services.tracer import tracer

    # A última mensagem é o bloco rag_context (garantido por _is_post_rag).
    rag_context_msg = all_messages[-1]

    user_question = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            user_question = str(msg.content)
            break

    payload: list = [
        SystemMessage(content=_RAG_SYNTHESIS_PROMPT),
        rag_context_msg,
        HumanMessage(content=user_question or "Responda com base no contexto acima."),
    ]

    answer = ""
    try:
        llm = _get_synthesis_llm()
        result = await llm.ainvoke(payload)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        answer = str(getattr(result, "content", "") or "").strip()
    except Exception as e:
        err_str = str(e)
        if _is_llm_quota_error(err_str):
            logger.warning("orchestrator: quota/rate-limit do LLM na síntese pós-RAG")
            retry_s = _extract_retry_delay(e)
            kind = _classify_quota_error(e)
            suffix = f":{retry_s}:{kind}" if retry_s else f":0:{kind}"
            answer = f"quota rate limit{suffix}"
        else:
            logger.warning("orchestrator: síntese pós-RAG falhou: %s", e)

    if not answer:
        answer = (
            "Não consegui sintetizar uma resposta a partir do contexto "
            "recuperado. Tente reformular a pergunta ou indexar a "
            "documentação relevante."
        )

    logger.info("Orchestrator: síntese pós-RAG → END (%d chars)", len(answer))

    session_id_int = int(session_id) if session_id and session_id.isdigit() else None
    with contextlib.suppress(Exception):
        async with tracer.span(
            "orchestrator", "rag_synthesis", session_id=session_id_int
        ) as s:
            s.set(answer_len=len(answer), question_len=len(user_question))

    return Command(
        goto=END,
        update={
            **state_update_extra,
            "routing_decision": "respond",
            "messages": [AIMessage(content=answer)],
        },  # type: ignore[arg-type]
    )


def _is_post_coder(state: State) -> bool:
    """True se `coder_finalize` acabou de rodar neste ciclo.

    O nó `coder_finalize` escreve `coder_result` (dict) em state antes de
    retornar ao orchestrator. Enquanto esse campo não for zerado (o que acontece
    durante a síntese aqui), a detecção é confiável.
    """
    return state.get("coder_result") is not None


def _is_post_search(state: State) -> bool:
    """True se `search_finalize` acabou de rodar neste ciclo.

    Análogo a `_is_post_coder` para o search agent.
    """
    return state.get("search_result") is not None


async def _synthesize_after_coder(
    state: State,
    session_id: str | None,
    state_update_extra: dict,
) -> Command:
    """Síntese pós-coder: o coder_finalize produziu um resultado estruturado;
    aqui o orchestrator redige a resposta final e encerra o turno.

    Zera `coder_result` no state para que o próximo turno comece limpo.
    """
    from vectora.services.tracer import tracer

    coder_result = state.get("coder_result") or CoderResult(summary="Tarefa concluída.")
    all_messages = list(state.get("messages", []))

    user_question = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            user_question = str(msg.content)
            break

    # Formata o resultado estruturado para o LLM de síntese
    files_str = ", ".join(coder_result.get("files_changed") or []) or "nenhum"
    tests_str = "sim" if coder_result.get("tests_run") else "não"
    success_str = "sim" if coder_result.get("success", True) else "não"
    next_steps = coder_result.get("next_steps") or ""

    result_block = (
        f"## Resultado do Coder Agent\n\n"
        f"**Resumo:** {coder_result.get('summary', 'Tarefa concluída.')}\n"
        f"**Arquivos alterados:** {files_str}\n"
        f"**Testes rodaram:** {tests_str}\n"
        f"**Sucesso:** {success_str}\n"
    )
    if next_steps:
        result_block += f"**Próximos passos:** {next_steps}\n"

    payload: list = [
        SystemMessage(content=_CODER_SYNTHESIS_PROMPT),
        SystemMessage(content=result_block),
        HumanMessage(content=user_question or "Resuma o que foi feito."),
    ]

    answer = ""
    try:
        llm = _get_synthesis_llm()
        result = await llm.ainvoke(payload)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        answer = str(getattr(result, "content", "") or "").strip()
    except Exception as e:
        err_str = str(e)
        if _is_llm_quota_error(err_str):
            logger.warning("orchestrator: quota/rate-limit do LLM na síntese pós-coder")
            retry_s = _extract_retry_delay(e)
            kind = _classify_quota_error(e)
            suffix = f":{retry_s}:{kind}" if retry_s else f":0:{kind}"
            answer = f"quota rate limit{suffix}"
        else:
            logger.warning("orchestrator: síntese pós-coder falhou: %s", e)
            # Fallback: usa o resumo estruturado diretamente
            answer = coder_result.get("summary", "Tarefa concluída.")

    if not answer:
        answer = coder_result.get("summary", "Tarefa concluída.")

    logger.info("Orchestrator: síntese pós-coder → END (%d chars)", len(answer))

    session_id_int = int(session_id) if session_id and session_id.isdigit() else None
    with contextlib.suppress(Exception):
        async with tracer.span(
            "orchestrator", "coder_synthesis", session_id=session_id_int
        ) as s:
            s.set(
                answer_len=len(answer),
                files=len(coder_result.get("files_changed") or []),
            )

    return Command(
        goto=END,
        update={
            **state_update_extra,
            "routing_decision": "respond",
            "coder_result": None,  # zera para o próximo turno
            "messages": [AIMessage(content=answer)],
        },  # type: ignore[arg-type]
    )


async def _synthesize_after_search(
    state: State,
    session_id: str | None,
    state_update_extra: dict,
) -> Command:
    """Síntese pós-search: o search_finalize produziu um resultado estruturado;
    aqui o orchestrator redige a resposta final e encerra o turno.

    Zera `search_result` no state para que o próximo turno comece limpo.
    """
    from vectora.services.tracer import tracer

    search_result = state.get("search_result") or SearchResult(
        summary="Pesquisa concluída."
    )
    all_messages = list(state.get("messages", []))

    user_question = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            user_question = str(msg.content)
            break

    sources = search_result.get("sources") or []
    sources_str = (
        "\n".join(f"- {s}" for s in sources) if sources else "nenhuma fonte registrada"
    )
    confidence = search_result.get("confidence", 0.7)
    web_str = "sim" if search_result.get("web_search_used") else "não"

    result_block = (
        f"## Resultado do Search Agent\n\n"
        f"**Resumo:** {search_result.get('summary', 'Pesquisa concluída.')}\n"
        f"**Busca web usada:** {web_str}\n"
        f"**Confiança:** {confidence:.0%}\n"
        f"**Fontes:**\n{sources_str}\n"
    )

    payload: list = [
        SystemMessage(content=_SEARCH_SYNTHESIS_PROMPT),
        SystemMessage(content=result_block),
        HumanMessage(content=user_question or "Resuma o que foi encontrado."),
    ]

    answer = ""
    try:
        llm = _get_synthesis_llm()
        result = await llm.ainvoke(payload)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        answer = str(getattr(result, "content", "") or "").strip()
    except Exception as e:
        err_str = str(e)
        if _is_llm_quota_error(err_str):
            logger.warning(
                "orchestrator: quota/rate-limit do LLM na síntese pós-search"
            )
            retry_s = _extract_retry_delay(e)
            kind = _classify_quota_error(e)
            suffix = f":{retry_s}:{kind}" if retry_s else f":0:{kind}"
            answer = f"quota rate limit{suffix}"
        else:
            logger.warning("orchestrator: síntese pós-search falhou: %s", e)
            answer = search_result.get("summary", "Pesquisa concluída.")

    if not answer:
        answer = search_result.get("summary", "Pesquisa concluída.")

    logger.info("Orchestrator: síntese pós-search → END (%d chars)", len(answer))

    session_id_int = int(session_id) if session_id and session_id.isdigit() else None
    with contextlib.suppress(Exception):
        async with tracer.span(
            "orchestrator", "search_synthesis", session_id=session_id_int
        ) as s:
            s.set(answer_len=len(answer), sources=len(sources))

    return Command(
        goto=END,
        update={
            **state_update_extra,
            "routing_decision": "respond",
            "search_result": None,  # zera para o próximo turno
            "messages": [AIMessage(content=answer)],
        },  # type: ignore[arg-type]
    )


async def _synthesize_after_parallel(
    state: State,
    session_id: str | None,
    state_update_extra: dict,
) -> Command:
    """Síntese pós-parallel (C5): integra resultados de múltiplos agentes paralelos.

    Zera `parallel_results` e `parallel_tasks` no state para o próximo turno.
    """
    from vectora.services.tracer import tracer

    parallel_results: list = state.get("parallel_results") or []
    all_messages = list(state.get("messages", []))

    user_question = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            user_question = str(msg.content)
            break

    results_block = "## Resultados das Tasks Paralelas\n\n"
    for i, res in enumerate(parallel_results, 1):
        agent = res.get("agent", "agent")
        task = res.get("task", "")
        response = res.get("response", "")
        ok = "✓" if res.get("success", True) else "✗"
        results_block += f"### Task {i} ({agent}) {ok}\n"
        results_block += f"**Instrução:** {task}\n\n"
        results_block += f"{response}\n\n"

    payload: list = [
        SystemMessage(content=_PARALLEL_SYNTHESIS_PROMPT),
        SystemMessage(content=results_block),
        HumanMessage(content=user_question or "Integre os resultados acima."),
    ]

    answer = ""
    try:
        llm = _get_synthesis_llm()
        result = await llm.ainvoke(payload)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        answer = str(getattr(result, "content", "") or "").strip()
    except Exception as e:
        logger.warning("orchestrator: síntese pós-parallel falhou: %s", e)
        # Fallback: concatena respostas
        parts = [
            f"**{r.get('agent', 'agent')}:** {r.get('response', '')}"
            for r in parallel_results
            if r.get("success", True)
        ]
        answer = "\n\n".join(parts) or "Tasks executadas sem resposta."

    if not answer:
        answer = "Tasks paralelas executadas."

    logger.info(
        "Orchestrator: síntese pós-parallel → END (%d tasks, %d chars)",
        len(parallel_results),
        len(answer),
    )

    session_id_int = int(session_id) if session_id and session_id.isdigit() else None
    with contextlib.suppress(Exception):
        async with tracer.span(
            "orchestrator", "parallel_synthesis", session_id=session_id_int
        ) as s:
            s.set(n_tasks=len(parallel_results), answer_len=len(answer))

    return Command(
        goto=END,
        update={
            **state_update_extra,
            "routing_decision": "respond",
            "parallel_results": None,
            "parallel_tasks": None,
            "messages": [AIMessage(content=answer)],
        },  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Nó do grafo
# ---------------------------------------------------------------------------


async def orchestrator(state: State, config: RunnableConfig) -> Command:
    """Nó orchestrator: responde diretamente ou delega com task query explícita.

    Quando action == 'respond':
      - Injeta AIMessage(response) em messages
      - Roteia para END (routing_decision = 'respond')

    Quando action == 'delegate':
      - Seta orchestrator_task (task_query) no state
      - Roteia para coder / search / rag_subgraph
    """
    from vectora.services.tracer import tracer

    all_messages = list(state.get("messages", []))

    session_id: str | None = None
    with contextlib.suppress(Exception):
        session_id = str(state.get("session_metadata", {}).get("thread_id", ""))  # type: ignore[assignment]
        if not session_id:
            session_id = None

    # --- Contexto da sessão (B7) —————————————————————————————————————
    # Carregado uma vez por sessão e re-carregado quando o curator atualiza
    # o manifest (manifest_version muda). Invalidação em memória pura —
    # sem I/O por turno; a comparação de inteiro é O(1).
    state_update_extra: dict = {}

    # Resolve workspace_id: config > state
    workspace_id: str | None = None
    with contextlib.suppress(Exception):
        workspace_id = (config.get("configurable") or {}).get("workspace_id")
    if workspace_id is None:
        workspace_id = state.get("session_metadata", {}).get("workspace_id")  # type: ignore[call-overload]

    project_context: str | None = state.get("project_context")  # type: ignore[assignment]

    # Detecta se o manifest foi atualizado pelo curator desde o último carregamento
    _reload_context = project_context is None
    if not _reload_context and workspace_id:
        try:
            from vectora.services.workspace import workspace_registry

            ws = workspace_registry.get(workspace_id)
            if ws is not None:
                cached_version = state.get("session_metadata", {}).get(  # type: ignore[call-overload]
                    "manifest_version", -1
                )
                if ws.manifest_version > cached_version:
                    _reload_context = True
                    logger.info(
                        "orchestrator: manifest_version bump (%d → %d), recarregando contexto",
                        cached_version,
                        ws.manifest_version,
                    )
        except Exception:
            pass

    if _reload_context:
        project_context = _load_session_context(workspace_id)
        state_update_extra["project_context"] = project_context
        # Salva a versão do manifest carregada para detectar próximo bump
        if workspace_id:
            try:
                from vectora.services.workspace import workspace_registry

                ws = workspace_registry.get(workspace_id)
                if ws is not None:
                    sm = dict(state.get("session_metadata") or {})
                    sm["manifest_version"] = ws.manifest_version
                    state_update_extra["session_metadata"] = sm
            except Exception:
                pass
        if project_context:
            logger.info("session_context carregado (%d chars)", len(project_context))

    # --- Modos pós-sub-agent (RAG / coder / search) ---
    # Quando um sub-agent finaliza, o orchestrator retorna ao grafo para
    # sintetizar a resposta final. Cada caminho vai SEMPRE para END com um LLM
    # plano, eliminando qualquer possibilidade de re-rotear ao mesmo sub-agent.

    if _is_post_rag(all_messages):
        # Subgrafo RAG injetou SystemMessage(name="rag_context") — sintetiza.
        return await _synthesize_after_rag(all_messages, session_id, state_update_extra)

    if _is_post_coder(state):
        # coder_finalize escreveu `coder_result` em state — sintetiza.
        return await _synthesize_after_coder(state, session_id, state_update_extra)

    if _is_post_search(state):
        # search_finalize escreveu `search_result` em state — sintetiza.
        return await _synthesize_after_search(state, session_id, state_update_extra)

    # C5 — parallel_dispatch escreveu `parallel_results` em state — sintetiza.
    if state.get("parallel_results"):
        return await _synthesize_after_parallel(state, session_id, state_update_extra)

    context_messages = _select_context_messages(all_messages)
    context_block = _build_context_block(state, session_id)

    last_human_text = ""
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            last_human_text = str(msg.content)
            break

    # L4 — instrução personalizada do usuário (prefixada ao prompt principal)
    custom_system_prompt: str = ""
    with contextlib.suppress(Exception):
        custom_system_prompt = (config.get("configurable") or {}).get(
            "custom_system_prompt", ""
        )

    # Montar payload para o LLM
    llm_messages: list = []
    if custom_system_prompt:
        llm_messages.append(
            SystemMessage(
                content=f"## Instrução personalizada do usuário\n\n{custom_system_prompt}",
                name="custom_instruction",
            )
        )
    if project_context:
        llm_messages.append(
            SystemMessage(
                content=f"## Contexto do Projeto\n\n{project_context}",
                name="project_context",
            )
        )
    llm_messages.append(SystemMessage(content=_ORCHESTRATOR_PROMPT))
    if context_block:
        llm_messages.append(SystemMessage(content=context_block))
    llm_messages.extend(context_messages)

    # Invocar o LLM orchestrator
    action: str = "respond"
    response: str = ""
    delegate_to: str | None = None
    task_query: str | None = None
    parallel_tasks: list | None = None
    reason: str = "fallback"

    try:
        llm = _get_orchestrator_llm()
        result: OrchestratorDecision = await llm.ainvoke(llm_messages)  # type: ignore[assignment]  # ty: ignore[unresolved-attribute]
        action = result.action
        response = result.response or ""
        delegate_to = result.delegate_to
        task_query = result.task_query
        parallel_tasks = [t.model_dump() for t in (result.parallel_tasks or [])]
        reason = result.reason

        # Persistir memórias solicitadas pelo LLM (save_memories no schema).
        # Executadas diretamente em Python — o structured output impede tool
        # calls reais no modo with_structured_output(OrchestratorDecision).
        if result.save_memories:
            from vectora.tools.memory import save_memory as _save_memory

            for mem in result.save_memories:
                try:
                    await _save_memory.ainvoke(
                        {"key": mem.key, "content": mem.content}, config=config
                    )
                    logger.info("orchestrator: memória salva — key=%s", mem.key)
                except Exception as mem_exc:
                    logger.warning(
                        "orchestrator: falha ao salvar memória key=%s: %s",
                        mem.key,
                        mem_exc,
                    )

    except Exception as e:
        err_str = str(e)
        if _is_llm_quota_error(err_str):
            logger.warning("orchestrator: quota/rate-limit do LLM atingida")
            retry_s = _extract_retry_delay(e)
            suffix = f":{retry_s}" if retry_s else ""
            response = f"quota rate limit{suffix}"
        else:
            logger.warning("orchestrator LLM falhou, respondendo diretamente: %s", e)
            response = "Desculpe, ocorreu um erro interno. Tente novamente."

    # Raciocínio para Bloco D — gravado no state para que adapt_stream emita ThinkingEvent
    thinking_data: dict = {
        "reason": reason,
        "action": action,
        "delegate_to": delegate_to,
        "task_query": task_query,
    }

    # Determinar destino e update do state
    if action == "respond":
        agent_label = "direct (inline)"
        goto = END
        update: dict = {
            **state_update_extra,
            "routing_decision": "respond",
            "messages": [AIMessage(content=response)],
            "thinking": thinking_data,
        }
    elif action == "parallel" and parallel_tasks:
        # C5 — fan-out para parallel_dispatch
        agent_label = f"parallel ({len(parallel_tasks)} tasks)"
        goto = "parallel_dispatch"
        update = {
            **state_update_extra,
            "routing_decision": "parallel",
            "parallel_tasks": parallel_tasks,
            "parallel_results": None,  # limpa resultados anteriores
            "thinking": thinking_data,
        }
    else:
        # delegate
        agent_label = delegate_to or "direct (fallback)"
        resolved_goto = _AGENT_MAP.get(delegate_to or "", END)
        goto = resolved_goto
        update = {
            **state_update_extra,
            "routing_decision": delegate_to or "respond",
            "orchestrator_task": task_query,
            "thinking": thinking_data,
        }

    logger.info(
        "Orchestrator: '%s...' → %s | %s",
        last_human_text[:60],
        agent_label,
        reason,
    )

    session_id_int = int(session_id) if session_id and session_id.isdigit() else None
    with contextlib.suppress(Exception):
        async with tracer.span("orchestrator", "route", session_id=session_id_int) as s:
            s.set(
                action=action,
                routing=agent_label,
                task_query_len=len(task_query or ""),
                query_len=len(last_human_text),
            )

    return Command(
        goto=goto,
        update=update,  # type: ignore[arg-type]
    )
