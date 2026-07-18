"""Factory do agente Vectora usando create_deep_agent (harness canônico).

Substitui o StateGraph manual de src/graph.py. Expõe a mesma interface de
lifecycle (get_user_agent, awarm, aclose) consumida por
src/api/handlers/chat.py, garantindo zero alteração no caller.

Arquitetura:
    - Agente principal (orchestrator) construído via create_deep_agent.
    - Subagents "coder" e "search" como SubAgent dicts; prompts importados
      de src/agents/{coder,search}.py (E.B-2 extrai specs para módulos próprios).
    - HITL por middleware: build_middleware_stack monta o
      HumanInTheLoopMiddleware conforme o permission_mode, adicionado ao stack
      passado a create_deep_agent (padrão canônico do deepagents).
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
from typing import Any

from backend.agents._identity import VECTORA_IDENTITY
from backend.rbac import tool_policy
from backend.workspace.plugins import tools_version
from backend.workspace.skills import skills_version

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

## Your Role — Vectora Orchestrator

You are **Vectora**, the main assistant. You either answer directly OR
delegate to specialists using the `task()` tool. Never do both in the same
turn.

**Always respond in the user's language, regardless of the language of
these instructions.**

---

## When to answer directly

For greetings, conversation, general knowledge, RAG synthesis, and questions
that don't need filesystem, terminal, or web search:

Answer in plain markdown (headings, lists, bold, code blocks with triple
backticks when it makes sense) — no envelope or external wrapper. The
frontend renders the markdown directly.

---

## When to delegate with `task()`

Use `task()` for specialists:

- **`task(subagent_type="coder", description="detailed instruction")`** —
  filesystem, code, terminal, git, npm, pip, tests, folder
  indexing/embedding. Write the instruction as if delegating to a coworker
  who hasn't read the conversation.

- **`task(subagent_type="search", description="what to research")`** —
  real-time web search, URL fetch, current internet information.

### How to write the instruction

- **Right:** "Create `src/utils/formatDate.ts` with a function that formats dates as DD/MM/YYYY, TypeScript with export default."
- **Right:** "Search the official LangGraph site for how to implement checkpointing with SQLite in Python."
- **Wrong:** "The user wants to create a file" (too vague)
- **Wrong:** Repeating the entire history

---

## Parallel execution

For genuinely independent tasks, call multiple `task()` in the same turn.
deepagents runs them in parallel automatically.

Valid example — "Research X and also check code Y":
- `task(subagent_type="search", description="Research X")`
- `task(subagent_type="coder", description="Check code Y")`

---

## Persistent memory

When the user shares personal information (name, occupation, projects,
preferred stack, language, location, preferences), use `save_memory`
immediately — without asking permission. Briefly confirm in your reply.

Use `get_memory` or `search_memory` before answering about the user.

---

## Artifacts — structured documents

When the user asks for a plan, spec, task list, guide, or architecture doc
**to save as a document**:
- Use `create_artifact` with type: `plan`, `spec`, `task_list`, `overview`,
  `guide`, `architecture`, or `implementation`.
- Confirm with the generated file's path.

---

## Git workflow

When the workspace contains a git repository, prefer safe flows:

- **Before large changes**: create a branch — delegate to the coder with
  `git_branch create feature-X` instructions.
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`, `chore:`). Never "wip" or vague messages.
- **Force push to main/master**: NEVER without explicit user confirmation.

---

## Creator identity

Vectora's creator and operator is **Bruno Soares** (`https://github.com/brunosrz`).
Acknowledge him based on this system prompt — no RAG, no web search.

---

## Absolute rules

1. If the user explicitly names an agent, ALWAYS respect it.
2. Creating/editing files, running code, git → **coder**.
3. Web search, URL fetch → **search**.
4. Queries against already-indexed documents → call `vector_search` or `search_memory` directly.
5. Indexing/embedding requests → **coder** with `ingest_docs`.
6. Fallback: when in doubt between answering and delegating → **answer directly**.
"""

# ---------------------------------------------------------------------------
# Subagent specs
# ---------------------------------------------------------------------------


def _subagent_specs(user_id: str | None = None) -> list[Any]:
    """Retorna a lista de SubAgent specs filtrada pela política de tools.

    Importações lazy evitam circular imports e carregamento desnecessário
    em contextos que não instanciam o grafo (CLI, testes unitários).

    As tools de cada subagent são filtradas removendo as que constam em
    ``tool_policy.effective_disabled(user_id)`` — união do disable global
    (admin kill-switch) com o ABAC por usuário. O disable global se aplica
    mesmo sem ``user_id`` (sessão local sem auth).

    As specs base são definidas em ``src/agents/{coder,search}.py`` como
    ``SUBAGENT_SPEC`` — ponto único de verdade para nome, descrição e tools.
    """
    import copy

    from backend.agents.coder import SUBAGENT_SPEC as CODER_SPEC
    from backend.agents.search import SUBAGENT_SPEC as SEARCH_SPEC

    specs = [copy.copy(CODER_SPEC), copy.copy(SEARCH_SPEC)]

    disabled = tool_policy.effective_disabled(user_id)
    if disabled:
        for spec in specs:
            spec["tools"] = [t for t in spec["tools"] if t.name not in disabled]
        logger.debug(
            "agent_factory: subagent tools filtradas user=%s disabled=%s",
            user_id,
            disabled,
        )

    return specs


# ---------------------------------------------------------------------------
# Context loader — injetado no system prompt por turno
# ---------------------------------------------------------------------------


def _load_project_docs() -> str | None:
    """Carrega arquivos de instrução do projeto e contexto do .vectora/.

    Coleta (em ordem de prioridade por weight):
    1. Arquivos de instrução na raiz: AGENTS.md, CLAUDE.md, GEMINI.md, VECTORA.md, …
    2. Todos os .md em .vectora/ com enabled=true (exceto MANIFEST.md e subpastas reservadas)

    Frontmatter YAML/Paperclip é parseado — campos weight, inject_when, enabled,
    truncate_at, title, description e tags são respeitados. Arquivos com
    inject_when='on_request' são omitidos do system prompt (disponíveis via tool).

    Retorna conteúdo formatado ou None se não encontrar nada.
    """
    from backend.services.context_files import (
        collect_context_files,
        format_context_files_for_prompt,
    )

    cwd = Path.cwd()
    files = collect_context_files(str(cwd))
    if not files:
        return None

    text = format_context_files_for_prompt(files, include_on_request=False)
    return text or None


def _load_workspaces_overview(active_id: str | None = None) -> str | None:
    """Lista os workspaces registrados para o Vectora ter consciência deles.

    O Vectora gerencia projetos isolados por diretório (workspaces). Injetar a
    lista no system prompt dá conhecimento proativo — o agente sabe quais
    projetos conhece sem precisar chamar `workspace_list`, e pode sugerir trocar
    de workspace quando a pergunta for sobre outro projeto.

    Retorna None se não houver nenhum workspace registrado.
    """
    try:
        from backend.workspace.workspace import workspace_registry

        workspaces = workspace_registry.list_all()
    except Exception:
        logger.debug("Falha ao listar workspaces para o contexto", exc_info=True)
        return None

    if not workspaces:
        return None

    lines: list[str] = [
        "## Seus Workspaces",
        "",
        "Você gerencia estes projetos isolados (cada um com diretório, base RAG e "
        "MANIFEST.md próprios). O marcado com ◀ é o ativo desta sessão:",
        "",
    ]
    # Limita a 30 entradas para não inflar o contexto; o restante via `workspace_list`.
    for ws in workspaces[:30]:
        marker = " ◀ ativo" if active_id and ws.id == active_id else ""
        git = " · git" if getattr(ws, "is_git_repo", False) else ""
        lines.append(f"- **{ws.name}** (`{ws.id}`) — `{ws.cwd}`{git}{marker}")
    if len(workspaces) > 30:
        lines.append(f"- … e mais {len(workspaces) - 30} (use `workspace_list`).")
    lines.append(
        "\nUse `workspace_describe`/`bucket_summary` para detalhes de um workspace "
        "e `vector_search` para buscar no conhecimento indexado do ativo."
    )
    return "\n".join(lines)


def _load_session_context(workspace_id: str | None = None) -> str | None:
    """Carrega contexto completo da sessão: arquivos de projeto + manifest do workspace.

    Seções:
    1. AGENTS.md / CLAUDE.md / VECTORA.md / GEMINI.md — instrução do projeto
    2. Lista de workspaces registrados (consciência dos projetos do Vectora)
    3. MANIFEST.md do workspace ativo — base de conhecimento indexada

    O manifest é truncado a ~3200 chars para não inflar o contexto. Detalhes
    por bucket ficam disponíveis via `bucket_summary` (tool sob demanda).
    """
    parts: list[str] = []

    project_docs = _load_project_docs()
    if project_docs:
        parts.append(project_docs)

    workspaces_overview = _load_workspaces_overview(workspace_id)
    if workspaces_overview:
        parts.append(workspaces_overview)

    if workspace_id:
        try:
            from backend.workspace.workspace import workspace_registry

            ws = workspace_registry.get(workspace_id)
            if ws is not None:
                manifest_path = ws.manifest_path()
                if manifest_path.exists():
                    raw_manifest = manifest_path.read_text(
                        encoding="utf-8", errors="ignore"
                    ).strip()
                    from backend.services.context_files import parse_frontmatter

                    _, manifest = parse_frontmatter(raw_manifest)
                    manifest = manifest.strip()
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


def _build_session_system_prompt(
    workspace_id: str | None = None,
) -> str:
    """Monta system prompt completo com contexto da sessão.

    Concatena o prompt base do orchestrator com:
    1. AGENTS.md / CLAUDE.md / GEMINI.md do workspace (se existirem)
    2. MANIFEST.md do workspace ativo (truncado)

    Chamado a cada compilação do grafo — lazy e cacheado via singleton.
    """
    try:
        ctx = _load_session_context(workspace_id)
        if ctx:
            return _ORCHESTRATOR_PROMPT + f"\n\n---\n\n## Contexto do Projeto\n\n{ctx}"
    except Exception:
        pass
    return _ORCHESTRATOR_PROMPT


# ---------------------------------------------------------------------------
# Singleton do grafo
# ---------------------------------------------------------------------------

# Cache de grafos compilados por modelo (`model_id` "provider:model"; "" = o
# padrão de env/settings). A troca de modelo por request constrói/reusa um
# grafo por modelo — o deepagents não aceita modelo configurável, então cada
# modelo tem seu grafo, todos compartilhando o MESMO checkpointer + store
# (uma única conexão SQLite, sem disputa de lock).
_graphs: dict[str, Any] = {}
_graphs_by_user: dict[tuple[str, str], Any] = {}  # (user_id, model) → graph (DE-5)
_checkpointer_ctx: Any = None
_checkpointer: Any = None
_store: Any = None
_store_ctx: Any = None  # context manager do store Postgres (complete mode)
_lock = asyncio.Lock()
_profiles_registered: bool = False

# Rastreia (tools_version, policy_version, skills_version) por usuário.
# Quando qualquer versão muda, o cache de LLM do usuário é invalidado.
_version_tracker: dict[str, tuple[int, int, int]] = {}

# Última versão observada da política global de tools (kill-switch do admin,
# tool_policy.GLOBAL_SCOPE). Diferente de _version_tracker (por usuário): o
# toggle global afeta TODAS as sessões, então invalida os dois caches inteiros
# em vez de fazer bookkeeping por chave.
_global_tools_version: int | None = None


def _agents_md_paths() -> list[str] | None:
    """Retorna os paths de AGENTS.md que o MemoryMiddleware deve carregar.

    Carrega (em ordem) o AGENTS.md global do Vectora e o AGENTS.md do
    workspace ativo, se existir. O harness lê e injeta o conteúdo no
    system prompt antes de cada turno.

    Retorna None se nenhum arquivo existir (desativa MemoryMiddleware).
    """
    paths: list[str] = []
    global_agents_md = Path.home() / ".vectora" / "AGENTS.md"
    if global_agents_md.is_file():
        paths.append(str(global_agents_md))
    return paths or None


async def _ensure_infra() -> None:
    """Abre (uma única vez) o checkpointer + store compartilhados.

    Todos os grafos (um por modelo) reusam estes recursos — assim há uma só
    conexão com o checkpointer, sem disputa de lock entre grafos.

    Em ``storage_mode="complete"`` com ``postgres_dsn`` configurado, usa
    ``AsyncPostgresSaver``/``AsyncPostgresStore`` (schema real, sem gargalo de
    lock de arquivo único) — antes disso o modo complete tinha Qdrant/Redis
    de verdade mas o checkpointer/store continuavam presos no SQLite,
    independente do modo escolhido. Fallback: qualquer falha ao abrir o
    Postgres (DSN ruim, banco fora do ar) degrada pro SQLite, para uma
    sessão nunca deixar de iniciar por causa de storage.
    """
    global _checkpointer_ctx, _checkpointer, _store, _store_ctx

    if _checkpointer is None:
        from backend.settings import settings as _settings

        if _settings.storage_mode == "complete" and _settings.postgres_dsn:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

                dsn = _settings.postgres_dsn.replace(
                    "postgresql+asyncpg://", "postgresql://"
                )
                _checkpointer_ctx = AsyncPostgresSaver.from_conn_string(dsn)
                _checkpointer = await _checkpointer_ctx.__aenter__()
                await _checkpointer.setup()
                logger.info(
                    "agent_factory: checkpointer Postgres ativo (storage_mode=complete)"
                )
            except Exception:
                logger.warning(
                    "agent_factory: falha ao abrir checkpointer Postgres, caindo pro SQLite",
                    exc_info=True,
                )
                _checkpointer_ctx = None
                _checkpointer = None

        if _checkpointer is None:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            db_path = str(Path.home() / ".vectora" / "checkpoints.db")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(db_path)
            _checkpointer = await _checkpointer_ctx.__aenter__()
            # from_conn_string não aplica nenhum PRAGMA (nem WAL, nem
            # busy_timeout) — sem isso, duas sessões/workspaces escrevendo ao
            # mesmo tempo no mesmo checkpoints.db batem em "database is
            # locked" na hora em vez de esperar (D2). Mesmos PRAGMAs do pool
            # hardened de backend/storage/sqlite/pool.py.
            await _checkpointer.conn.executescript(
                "PRAGMA journal_mode=WAL;"
                "PRAGMA busy_timeout=30000;"
                "PRAGMA synchronous=NORMAL;"
            )

    if _store is None:
        from backend.settings import settings as _settings

        if _settings.storage_mode == "complete" and _settings.postgres_dsn:
            try:
                from langgraph.store.postgres.aio import AsyncPostgresStore

                dsn = _settings.postgres_dsn.replace(
                    "postgresql+asyncpg://", "postgresql://"
                )
                _store_ctx = AsyncPostgresStore.from_conn_string(dsn)
                _store = await _store_ctx.__aenter__()
                await _store.setup()
                logger.info(
                    "agent_factory: store Postgres ativo (storage_mode=complete)"
                )
            except Exception:
                logger.warning(
                    "agent_factory: falha ao abrir store Postgres, caindo pro SQLite",
                    exc_info=True,
                )
                _store_ctx = None
                _store = None

        if _store is None:
            from backend.llm.backends import build_store

            _store = await build_store()


async def get_store() -> Any:
    """Retorna o LangGraph BaseStore compartilhado (mesmo usado pelo agente).

    Diferente de ``langgraph.config.get_store()`` (que só funciona dentro de
    um grafo em execução, via contextvar), este getter devolve a instância
    direta — para uso em handlers HTTP fora do ciclo de vida do grafo, que
    precisam ler/escrever o mesmo namespace que as memory tools do agente.
    """
    await _ensure_infra()
    return _store


async def _build_graph_async(
    model_id: str = "",
    chat_mode: bool = False,
    user_id: str | None = None,
    permission_mode: str = "ask",
) -> Any:
    """Compila um grafo deepagents para ``model_id`` (checkpointer/store compartilhados).

    Não muta estado global de cache — quem cacheia é ``get_user_agent``. Vazio
    em ``model_id`` usa o modelo padrão de env/settings. Em ``chat_mode`` o agente
    é conversacional puro: ``CHAT_TOOLS`` (sem fs/git/terminal/workspace) e sem
    subagents de dev. ``user_id`` filtra a toolset principal e a dos subagents
    por ``tool_policy.effective_disabled`` (kill-switch global + ABAC).
    ``permission_mode`` determina o comportamento de HITL (ver
    ``backend.services.middleware.build_middleware_stack``) — cada modo com
    ``interrupt_on`` distinto tem seu próprio grafo compilado e cacheado.
    """
    await _ensure_infra()

    from typing import cast as _cast

    from deepagents import create_deep_agent
    from langchain_core.language_models.chat_models import BaseChatModel

    from backend.llm.fallback_chat_model import FallbackChatModel
    from backend.nodes.tools import ALL_TOOLS, CHAT_TOOLS

    # FallbackChatModel envolve o LLM do modelo escolhido: em 429/quota antes do
    # primeiro token, troca para o próximo provider de `fallback_order` (lido em
    # runtime), registrando a troca p/ o handler de chat notificar a UI. Cadeia
    # vazia → delega ao primário de forma transparente (sem overhead semântico).
    llm: BaseChatModel = _cast(
        "BaseChatModel", FallbackChatModel(primary_model_id=model_id)
    )
    tools = CHAT_TOOLS if chat_mode else ALL_TOOLS
    disabled = tool_policy.effective_disabled(user_id)
    if disabled:
        tools = [t for t in tools if t.name not in disabled]
        logger.debug(
            "agent_factory: tools principais filtradas user=%s disabled=%s",
            user_id,
            disabled,
        )
    # Chat puro não usa subagents (coder/search são orientados a dev/filesystem).
    subagents = [] if chat_mode else _subagent_specs(user_id)

    system_prompt = _build_session_system_prompt()

    global _profiles_registered
    if not _profiles_registered:
        from backend.workspace.profiles import _register_profiles

        _register_profiles()
        _profiles_registered = True

    # Middleware stack: HumanInTheLoopMiddleware conforme permission_mode.
    # create_deep_agent já adiciona SummarizationMiddleware ao stack base
    # incondicionalmente. Cada permission_mode com interrupt_on distinto tem
    # seu próprio grafo compilado e cacheado (ver get_user_agent).
    from backend.services.middleware import build_middleware_stack

    middleware = build_middleware_stack(permission_mode=permission_mode)

    from backend.llm.backends import build_backend_lazy
    from backend.vtypes.context import VectoraContext
    from backend.workspace.skills import list_skill_paths

    # Skills instaladas pelo usuário local (singleton compartilhado).
    # Paths absolutos — harness lê SKILL.md frontmatter on-demand.
    skill_paths = [str(p) for p in list_skill_paths("local")]

    # AGENTS.md paths para o MemoryMiddleware — injetado no system prompt.
    memory_paths = _agents_md_paths()

    compiled = create_deep_agent(
        llm,
        tools=tools,
        system_prompt=system_prompt,
        subagents=subagents,
        middleware=middleware,
        backend=build_backend_lazy(),
        checkpointer=_checkpointer,
        context_schema=VectoraContext,
        skills=skill_paths,
        store=_store,
        memory=memory_paths,
        name="vectora",
    )

    # O grafo é consumido via `astream_events` no handler de chat para
    # streaming de tokens em tempo real. NÃO envolvemos em `with_retry`
    # (RunnableRetry): o retry precisa poder reexecutar a chamada de forma
    # atômica, então bufferiza a saída inteira — o cliente só veria a resposta
    # ao final, sem streaming. Além disso, num 429 o retry insistia 3x com
    # backoff (até ~30s) antes de surgir o erro. Erros transientes do provider
    # são tratados pelo `max_retries` do próprio modelo (nível da chamada LLM,
    # não quebra o stream) e classificados/limpos em `adapters.classify_stream_error`.
    logger.info(
        "agent_factory: grafo compilado (model=%r, chat_mode=%s, deepagents + %d tools + %d subagents + %d middleware)",
        model_id or "default",
        chat_mode,
        len(tools),
        len(subagents),
        len(middleware),
    )
    return compiled


def _check_global_tools_version() -> None:
    """Se o kill-switch global de tools mudou, derruba TODOS os grafos em cache.

    Precisa rodar antes de qualquer lookup em ``_graphs``/``_graphs_by_user``
    (chamado no início de ``get_user_agent``), senão uma sessão já em cache
    continuaria usando o toolset antigo indefinidamente.
    """
    global _global_tools_version
    current = tool_policy.policy_version(tool_policy.GLOBAL_SCOPE)
    if _global_tools_version is not None and current != _global_tools_version:
        _graphs.clear()
        _graphs_by_user.clear()
        logger.info(
            "agent_factory: kill-switch global de tools mudou (v%d→v%d) — grafos invalidados",
            _global_tools_version,
            current,
        )
    _global_tools_version = current


#: permission_mode que produzem o MESMO interrupt_on (ver
#: middleware._interrupt_on_for_mode) — compartilham grafo compilado em vez de
#: cachear uma cópia idêntica por nome.
_PERMISSION_MODE_CACHE_KEY: dict[str, str] = {
    "bypass": "bypass",
    "auto": "bypass",
    "accept_edits": "accept_edits",
    "plan": "plan",
}


async def get_user_agent(
    user_id: str | None = None,
    model: str = "",
    chat_mode: bool = False,
    permission_mode: str = "ask",
) -> Any:
    """Retorna o grafo compilado para (user_id, model, chat_mode, permission_mode).

    Se user_id está presente: cacheia por (user_id, model_key). Se user_id é None:
    usa cache global por model_key. O ``chat_mode`` entra no ``model_key`` (sufixo
    ``#chat``) — chat e dev têm grafos compilados separados (toolsets diferentes).
    ``permission_mode`` entra como outro sufixo (``#<modo>``) SÓ quando o modo tem
    um ``interrupt_on`` distinto de "ask" (ver ``_PERMISSION_MODE_CACHE_KEY``) —
    isso é o que faz o modo "plan" ter comportamento de HITL realmente diferente
    de "ask" (antes, todo grafo era compilado com ``permission_mode="ask"`` fixo,
    e o valor por request em ``configurable`` nunca era lido em lugar nenhum).
    Todos compartilham checkpointer/store. Thread-safe via asyncio.Lock.

    A toolset é filtrada por ``tool_policy.effective_disabled(user_id)`` no
    momento da compilação (``_build_graph_async``); mudanças de política depois
    disso só valem a partir da próxima invalidação de cache (``_track_versions``
    por usuário, ``_check_global_tools_version`` para o kill-switch do admin).
    """
    _check_global_tools_version()

    base = model or "__default__"
    mode_suffix = _PERMISSION_MODE_CACHE_KEY.get(permission_mode, "")
    model_key = f"{base}#chat" if chat_mode else base
    if mode_suffix:
        model_key = f"{model_key}#{mode_suffix}"

    # DE-5: Cache por sessão (user_id, model_key)
    if user_id:
        session_key = (user_id, model_key)
        if session_key not in _graphs_by_user:
            async with _lock:
                if session_key not in _graphs_by_user:
                    _graphs_by_user[session_key] = await _build_graph_async(
                        model, chat_mode, user_id, permission_mode
                    )
        _track_versions(user_id)
        return _graphs_by_user[session_key]

    # Fallback: cache global por model_key
    if model_key not in _graphs:
        async with _lock:
            if model_key not in _graphs:
                _graphs[model_key] = await _build_graph_async(
                    model, chat_mode, user_id, permission_mode
                )

    return _graphs[model_key]


def _message_text(content: Any) -> str:
    """Extrai o texto de uma mensagem (str ou lista de partes multimodais).

    Mensagens AI modernas têm ``content`` como lista de blocos
    (``[{"type": "text", "text": ...}, ...]``); extrai e concatena só o texto.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


async def aget_thread_messages(thread_id: str) -> list[tuple[str, str, str]]:
    """Mensagens persistidas de uma thread como ``(role, text, checkpoint_id)``.

    Usa o grafo deepagents compilado (schema idêntico ao que escreveu os
    checkpoints) para ler o histórico via ``aget_state_history`` — não só o
    estado mais recente (``aget_state``), pra poder atribuir a cada mensagem o
    checkpoint pai (estado do thread imediatamente antes dela existir). Um
    grafo mínimo NOOP falha na desserialização porque não possui os canais
    internos do deepagents.

    O ``checkpoint_id`` devolvido por mensagem é o alvo de fork pra "editar e
    reenviar" (edita a própria mensagem) e "regenerar" (edita a última
    resposta do assistente) — resumir o grafo a partir dele faz o LangGraph
    ramificar dali, preservando o histórico original intacto (ver
    ``ChatConfig.fork_from_checkpoint_id`` em chat.py). Vazio quando não há
    checkpoint pai (raríssimo — thread sem nenhum estado gravado ainda).

    Filtra mensagens de tool e turnos AI sem texto — devolve transcript limpo.
    """
    await _ensure_infra()
    if _checkpointer is None:
        return []

    from langchain_core.runnables import RunnableConfig

    graph = await get_user_agent()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    try:
        # aget_state_history vem do mais recente pro mais antigo (LangGraph);
        # inverte pra processar em ordem cronológica e comparar snapshots
        # consecutivos.
        history = [snap async for snap in graph.aget_state_history(config)]
    except Exception:
        logger.debug(
            "aget_thread_messages: falha ao ler histórico thread=%s",
            thread_id,
            exc_info=True,
        )
        return []

    if not history:
        return []
    history.reverse()

    out: list[tuple[str, str, str]] = []
    prev_len = 0
    for snapshot in history:
        msgs = snapshot.values.get("messages", []) if snapshot.values else []
        new_msgs = msgs[prev_len:]
        if new_msgs:
            parent_config = snapshot.parent_config or {}
            parent_checkpoint_id = parent_config.get("configurable", {}).get(
                "checkpoint_id", ""
            )
            for msg in new_msgs:
                msg_type = getattr(msg, "type", "")
                if msg_type == "tool":
                    continue
                text = _message_text(getattr(msg, "content", "")).strip()
                if not text:
                    continue
                role = "human" if msg_type == "human" else "assistant"
                out.append((role, text, parent_checkpoint_id))
        prev_len = len(msgs)
    return out


async def aget_thread_todos(thread_id: str) -> list[dict[str, str]]:
    """Snapshot mais recente de ``state["todos"]`` (write_todos/
    TodoListMiddleware, injetado incondicionalmente pelo deepagents).

    Popula a seção "Tasks" do Plan tab num reload de página — o SSE ao vivo
    (``TodosUpdatedEvent``) já entrega isso em tempo real, mas não persiste
    em lugar nenhum entre streams; aqui lê direto do checkpoint, mesma fonte
    de verdade de ``aget_thread_messages``. Usa ``aget_state`` (só o
    snapshot mais recente), não ``aget_state_history`` — não precisa do
    histórico completo, só do estado atual.
    """
    await _ensure_infra()
    if _checkpointer is None:
        return []

    from langchain_core.runnables import RunnableConfig

    graph = await get_user_agent()
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = await graph.aget_state(config)
    except Exception:
        logger.debug(
            "aget_thread_todos: falha ao ler state thread=%s",
            thread_id,
            exc_info=True,
        )
        return []

    if not snapshot or not snapshot.values:
        return []
    return snapshot.values.get("todos", []) or []


def reset_default_graph() -> None:
    """Invalida o grafo do modelo padrão após troca de provider/model.

    ``apply_model_change`` muda o provider/modelo padrão (env/settings); o grafo
    ``"__default__"`` foi compilado com o LLM antigo e fica stale. O cache por
    modelo explícito (``"provider:model"``) continua válido. Requests em voo que
    já seguram o grafo antigo não são afetados — o próximo ``get_user_agent()``
    sem modelo recompila com o novo padrão.
    """
    _graphs.pop("__default__", None)
    logger.info("agent_factory: grafo do modelo padrão invalidado (troca de modelo)")


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
    """Remove os grafos compilados em cache do usuário (tools/policy/skills mudaram).

    Purga ``_graphs_by_user`` — o cache real consultado por ``get_user_agent``
    — para que a próxima chamada recompile com a toolset atualizada. Também
    limpa ``llm_tools._bound_cache`` (cache auxiliar por chave de versão).
    """
    try:
        stale_graph_keys = [k for k in _graphs_by_user if k[0] == user_id]
        for k in stale_graph_keys:
            del _graphs_by_user[k]

        from backend.llm import llm_tools

        stale_keys = [k for k in llm_tools._bound_cache if k[0] == user_id]
        for k in stale_keys:
            del llm_tools._bound_cache[k]
        if stale_graph_keys or stale_keys:
            logger.info(
                "agent_factory: %d grafo(s) + %d entrada(s) de LLM cache invalidados para %s",
                len(stale_graph_keys),
                len(stale_keys),
                user_id,
            )
    except Exception:
        pass


async def coder_compensate(workspace_id: str | None = None) -> str | None:
    """Rollback de emergência via ``git stash`` após falha catastrófica do coder.

    Chamado pelo handler de exceção quando o subagent coder falha após já ter
    começado a modificar arquivos. Executa ``git stash`` no workspace ativo
    para reverter mudanças não commitadas e deixar o repositório limpo.

    Args:
        workspace_id: ID do workspace para resolver o path. Se None, usa home.

    Returns:
        Stdout do ``git stash`` se bem-sucedido; None se não aplicável ou falhou.

    Nota:
        Execução silenciosa — falhas aqui não relançam exceção para não ofuscar
        o erro original que ativou a compensação.
    """
    import shutil
    import subprocess  # nosec B404 — git controlado, sem shell=True

    try:
        from backend.llm.backends import _resolve_workspace_root

        workspace_root = _resolve_workspace_root(workspace_id)
        if not (workspace_root / ".git").is_dir():
            logger.debug("coder_compensate: sem repositório git em %s", workspace_root)
            return None

        git_exe = shutil.which("git")
        if git_exe is None:
            return None

        result = subprocess.run(  # noqa: S603, ASYNC221  # nosec B603
            [
                git_exe,
                "-C",
                str(workspace_root),
                "stash",
                "--include-untracked",
                "--",
                ".",
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        output = result.stdout.decode("utf-8", errors="replace").strip()
        if result.returncode == 0:
            logger.warning("coder_compensate: git stash aplicado — %s", output or "ok")
        else:
            err = result.stderr.decode("utf-8", errors="replace").strip()
            logger.warning(
                "coder_compensate: git stash falhou (%d) — %s", result.returncode, err
            )
        return output or None
    except Exception as exc:
        logger.debug("coder_compensate: erro ignorado: %s", exc)
        return None


async def aclose() -> None:
    """Fecha o grafo + checkpointer/store (SQLite ou Postgres). Idempotente.

    Deve ser chamado no shutdown do FastAPI (lifespan).
    """
    global _checkpointer_ctx, _checkpointer, _store, _store_ctx

    async with _lock:
        if _checkpointer_ctx is None:
            return
        ctx = _checkpointer_ctx
        store_ctx = _store_ctx
        _checkpointer_ctx = None
        _checkpointer = None
        _store = None  # reaberto no próximo _ensure_infra
        _store_ctx = None
        _graphs.clear()
        _version_tracker.clear()
        try:
            await ctx.__aexit__(None, None, None)
            logger.info("agent_factory: checkpointer fechado")
        except Exception as exc:
            logger.warning("agent_factory: erro ao fechar checkpointer: %s", exc)
        if store_ctx is not None:
            try:
                await store_ctx.__aexit__(None, None, None)
                logger.info("agent_factory: store Postgres fechado")
            except Exception as exc:
                logger.warning("agent_factory: erro ao fechar store Postgres: %s", exc)


async def awarm() -> None:
    """Inicializa o grafo eagerly no startup (opt-in).

    Evita que a primeira request pague o custo de compilação (~3-5s).
    Falhas aqui não derrubam o servidor — apenas logam aviso.
    """
    try:
        await get_user_agent()
    except Exception as exc:
        logger.warning("agent_factory: awarm falhou: %s", exc)
