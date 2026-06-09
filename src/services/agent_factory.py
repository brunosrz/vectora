"""Factory do agente Vectora usando create_deep_agent (harness canônico).

Substitui o StateGraph manual de src/graph.py. Expõe a mesma interface de
lifecycle (get_user_agent, awarm, aclose) consumida por
src/api/handlers/chat.py, garantindo zero alteração no caller.

Arquitetura:
    - Agente principal (orchestrator) construído via create_deep_agent.
    - Subagents "coder" e "search" como SubAgent dicts; prompts importados
      de src/agents/{coder,search}.py (E.B-2 extrai specs para módulos próprios).
    - HITL por middleware: E.B-3 adiciona HumanInTheLoopMiddleware com leitura
      de permission_mode via runtime config. Nesta versão o HITL está desabilitado
      — interrupt_on omitido. # TODO: E.B-3
    - Checkpointer: AsyncSqliteSaver (F4 migra para AsyncPostgresSaver em
      STORAGE_MODE=complete).
    - Singleton compartilhado entre todos os usuários; versionamento por user
      via _version_tracker detecta rebind necessário de tools/policy/skills.

Cache:
    O grafo é compilado uma vez e compartilhado. A personalização por user fica
    nas tools (ABAC via tool_policy) e no contexto injetado no system prompt
    via configurable (user_name, language, workspace_id).

Lifecycle:
    Servidor: awarm() no startup, aclose() no shutdown.
    Testes: use fixtures que chamam aclose() no teardown.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.agents._identity import VECTORA_IDENTITY
from src.services import tool_policy
from src.services.plugins import tools_version
from src.services.skills import skills_version

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HITL configuration constants (preserved para compatibilidade com chat.py)
# ---------------------------------------------------------------------------

#: Tools destrutivas que pausam o grafo para aprovação do usuário.
REQUIRE_APPROVAL: frozenset[str] = frozenset(
    {"terminal", "terminal_tool", "file_write", "file_write_tool"}
)

#: Tools auto-aprovadas no modo "accept_edits".
ACCEPT_EDITS_AUTO: frozenset[str] = frozenset({"file_write", "file_write_tool"})


def get_interrupt_on(permission_mode: str) -> dict[str, bool]:
    """Mapeia permission_mode para interrupt_on.

    Preservado para compatibilidade com src/api/handlers/chat.py que lê
    este dict e o passa no configurable. Com deepagents, o HITL real é feito
    via HumanInTheLoopMiddleware (E.B-3) que lê permission_mode do context.
    """
    match permission_mode:
        case "bypass" | "auto":
            return {}
        case "accept_edits":
            return dict.fromkeys(REQUIRE_APPROVAL - ACCEPT_EDITS_AUTO, True)
        case _:  # "ask", "plan", ou desconhecido
            return dict.fromkeys(REQUIRE_APPROVAL, True)


# ---------------------------------------------------------------------------
# System prompt do orchestrator
# ---------------------------------------------------------------------------

_ORCHESTRATOR_PROMPT = f"""{VECTORA_IDENTITY}

---

## Seu Papel — Orchestrator Vectora

Você é o **Vectora**, assistente principal. Responde diretamente OU delega
a especialistas usando a tool `task()`. Nunca faz as duas coisas no mesmo turno.

---

## Quando responder diretamente

Para saudações, conversas, conhecimento geral, síntese RAG e perguntas que
não precisam de filesystem, terminal ou busca web:

Envolva **toda** resposta em markdown com **exatamente seis acentos graves**:

``````
``````markdown
# Título

Texto em markdown aqui.

```python
print("blocos internos funcionam")
```
``````
``````

Regras:
- Seis crases no abre e no fecha. Identificador: sempre `markdown`.
- Mesmo respostas curtas vão dentro do envelope.

---

## Quando delegar com `task()`

Use `task()` para especialistas:

- **`task(name="coder", task="instrução detalhada")`** — filesystem, código,
  terminal, git, npm, pip, testes, indexação/embedding de pastas.
  Escreva a instrução como se delegasse a um colega que não leu a conversa.

- **`task(name="search", task="o que pesquisar")`** — busca web em tempo real,
  fetch de URL, informação atual da internet.

### Como escrever a instrução

- **Certo:** "Crie `src/utils/formatDate.ts` com função que formata datas DD/MM/YYYY, TypeScript com export default."
- **Certo:** "Pesquise no site oficial do LangGraph como implementar checkpointing com SQLite em Python."
- **Errado:** "O usuário quer criar um arquivo" (vago demais)
- **Errado:** Repetir todo o histórico

---

## Execução paralela

Para tarefas genuinamente independentes, chame múltiplos `task()` no mesmo
turno. O deepagents executa em paralelo automaticamente.

Exemplo válido — "Pesquise X e também verifique o código Y":
- `task(name="search", task="Pesquise X")`
- `task(name="coder", task="Verifique o código Y")`

---

## Memória persistente

Quando o usuário compartilhar informação pessoal (nome, profissão, projetos,
stack preferida, idioma, localização, preferências), use `save_memory`
imediatamente — sem pedir permissão. Confirme brevemente na resposta.

Use `get_memory` ou `search_memory` antes de responder sobre o usuário.

---

## Artifacts — documentos estruturados

Quando o usuário pedir plano, spec, lista de tarefas, guia ou arquitetura
para **salvar como documento**:
- Use `create_artifact` com tipo: `plan`, `spec`, `task_list`, `overview`,
  `guide`, `architecture` ou `implementation`.
- Passe o `session_id` disponível no contexto.
- Confirme com o caminho do arquivo gerado.

---

## Git workflow

Quando o workspace contém um repositório git, prefira fluxos seguros:

- **Antes de modificações grandes**: crie uma branch — delegue ao coder com
  instruções de `git_branch create feature-X`.
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`, `chore:`). Nunca "wip" ou mensagens vagas.
- **Force push em main/master**: NUNCA sem confirmação explícita do usuário.

---

## Identidade do criador

O criador e operador do Vectora é **Bruno Soares** (`https://github.com/brunosrz`).
Reconheça-o com base neste system prompt — sem RAG, sem web search.

---

## Regras absolutas

1. Se o usuário nomear explicitamente um agent, respeite SEMPRE.
2. Criação/edição de arquivos, execução de código, git → **coder**.
3. Busca web, fetch de URL → **search**.
4. Consultas a documentos já indexados → chame `vector_search` ou `search_memory` diretamente.
5. Pedidos de indexação/embedding → **coder** com `ingest_docs`.
6. Fallback: se dúvida entre responder e delegar → **responda diretamente**.
"""

# ---------------------------------------------------------------------------
# Subagent specs
# ---------------------------------------------------------------------------


def _subagent_specs(user_id: str | None = None) -> list[Any]:
    """Retorna a lista de SubAgent specs filtrada pela política ABAC do usuário.

    Importações lazy evitam circular imports e carregamento desnecessário
    em contextos que não instanciam o grafo (CLI, testes unitários).

    Quando ``user_id`` é fornecido, as tools de cada subagent são filtradas
    removendo as que constam em ``tool_policy.get_disabled(user_id)``.
    Sem ``user_id`` (padrão), retorna o toolset completo.

    As specs base são definidas em ``src/agents/{coder,search}.py`` como
    ``SUBAGENT_SPEC`` — ponto único de verdade para nome, descrição e tools.
    """
    import copy

    from src.agents.coder import SUBAGENT_SPEC as CODER_SPEC
    from src.agents.search import SUBAGENT_SPEC as SEARCH_SPEC

    specs = [copy.copy(CODER_SPEC), copy.copy(SEARCH_SPEC)]

    if user_id:
        disabled: set[str] = set(tool_policy.get_disabled(user_id))
        if disabled:
            for spec in specs:
                spec["tools"] = [t for t in spec["tools"] if t.name not in disabled]
            logger.debug(
                "agent_factory: subagent tools filtradas por ABAC user=%s disabled=%s",
                user_id,
                disabled,
            )

    return specs


# ---------------------------------------------------------------------------
# Context loader — injetado no system prompt por turno
# ---------------------------------------------------------------------------


def _build_session_system_prompt(
    workspace_id: str | None = None,
) -> str:
    """Monta system prompt completo com contexto da sessão.

    Concatena o prompt base do orchestrator com:
    1. AGENTS.md / CLAUDE.md / GEMINI.md do workspace (se existirem)
    2. MANIFEST.md do workspace ativo (truncado)

    Chamado a cada compilação do grafo — lazy e cacheado via singleton.
    """
    # Importa utilities de contexto do orchestrator (evita duplicação)
    try:
        from src.agents.orchestrator import _load_session_context

        ctx = _load_session_context(workspace_id)
        if ctx:
            return _ORCHESTRATOR_PROMPT + f"\n\n---\n\n## Contexto do Projeto\n\n{ctx}"
    except Exception:
        pass
    return _ORCHESTRATOR_PROMPT


# ---------------------------------------------------------------------------
# Singleton do grafo
# ---------------------------------------------------------------------------

_graph: Any = None
_checkpointer_ctx: Any = None
_lock = asyncio.Lock()

# Rastreia (tools_version, policy_version, skills_version) por usuário.
# Quando qualquer versão muda, o cache de LLM do usuário é invalidado.
_version_tracker: dict[str, tuple[int, int, int]] = {}


async def _build_graph_async() -> Any:
    """Compila o grafo deepagents e abre o checkpointer SQLite."""
    global _graph, _checkpointer_ctx

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from src.nodes.tools import ALL_TOOLS
    from src.services.utils import load_llm

    db_path = str(Path.home() / ".vectora" / "checkpoints.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(db_path)
    checkpointer = await _checkpointer_ctx.__aenter__()

    from typing import cast as _cast

    from deepagents import create_deep_agent
    from langchain_core.language_models.chat_models import BaseChatModel

    # load_llm() retorna BaseChatModel em runtime; a anotação usa a base mais genérica.
    llm: BaseChatModel = _cast("BaseChatModel", load_llm())
    subagents = _subagent_specs()  # sem user_id: toolset completo no singleton

    system_prompt = _build_session_system_prompt()

    # Registra perfis de harness por provider (Anthropic/Gemini/Ollama).
    # Idempotente — safe chamar múltiplas vezes.
    from src.services.profiles import _register_profiles

    _register_profiles()

    # Middleware stack: SummarizationMiddleware (compressão de contexto) +
    # HumanInTheLoopMiddleware com mode="ask" para o singleton compartilhado.
    # E.B-5 (context_schema=VectoraContext) permitirá modo dinâmico por usuário.
    from src.services.middleware import build_middleware_stack

    middleware = build_middleware_stack(permission_mode="ask", llm=llm)

    from src.types.context import VectoraContext

    _graph = create_deep_agent(
        llm,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        subagents=subagents,
        middleware=middleware,
        checkpointer=checkpointer,
        context_schema=VectoraContext,
        name="vectora",
    )

    logger.info(
        "agent_factory: grafo compilado (deepagents + %d tools + %d subagents + %d middleware)",
        len(ALL_TOOLS),
        len(subagents),
        len(middleware),
    )
    return _graph


async def get_user_agent(user_id: str | None = None) -> Any:
    """Retorna o grafo compilado (singleton compartilhado entre usuários).

    Garante inicialização thread-safe via asyncio.Lock. Registra a versão
    atual de tools/policy/skills do usuário para detectar necessidade de
    rebind; quando muda, invalida o cache do LLM bound em llm_tools.
    """
    if _graph is None:
        async with _lock:
            if _graph is None:
                await _build_graph_async()

    if user_id:
        _track_versions(user_id)

    return _graph


def _track_versions(user_id: str) -> None:
    """Atualiza rastreamento de versão sem bloquear o caller."""
    try:
        tv = tools_version(user_id)
        pv = tool_policy.policy_version(user_id)
        sv = skills_version(user_id)
        prev = _version_tracker.get(user_id)
        if prev != (tv, pv, sv):
            _version_tracker[user_id] = (tv, pv, sv)
            if prev is not None:
                _invalidate_llm_cache(user_id)
    except Exception:
        pass


def _invalidate_llm_cache(user_id: str) -> None:
    """Remove entradas stale do cache de LLM bound (llm_tools._bound_cache)."""
    try:
        from src.services import llm_tools

        stale_keys = [k for k in llm_tools._bound_cache if k[0] == user_id]
        for k in stale_keys:
            del llm_tools._bound_cache[k]
        if stale_keys:
            logger.debug(
                "agent_factory: %d entradas de LLM cache invalidadas para %s",
                len(stale_keys),
                user_id,
            )
    except Exception:
        pass


async def aclose() -> None:
    """Fecha o grafo + checkpointer SQLite. Idempotente.

    Deve ser chamado no shutdown do FastAPI (lifespan).
    """
    global _graph, _checkpointer_ctx

    async with _lock:
        if _checkpointer_ctx is None:
            return
        ctx = _checkpointer_ctx
        _checkpointer_ctx = None
        _graph = None
        _version_tracker.clear()
        try:
            await ctx.__aexit__(None, None, None)
            logger.info("agent_factory: checkpointer fechado")
        except Exception as exc:
            logger.warning("agent_factory: erro ao fechar checkpointer: %s", exc)


async def awarm() -> None:
    """Inicializa o grafo eagerly no startup (opt-in).

    Evita que a primeira request pague o custo de compilação (~3-5s).
    Falhas aqui não derrubam o servidor — apenas logam aviso.
    """
    try:
        await get_user_agent()
    except Exception as exc:
        logger.warning("agent_factory: awarm falhou: %s", exc)
