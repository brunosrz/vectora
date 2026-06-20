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
from backend.services import tool_policy
from backend.services.plugins import tools_version
from backend.services.skills import skills_version

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

    from backend.agents.coder import SUBAGENT_SPEC as CODER_SPEC
    from backend.agents.search import SUBAGENT_SPEC as SEARCH_SPEC

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
        from backend.agents.orchestrator import _load_session_context

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
_checkpointer_ctx: Any = None
_checkpointer: Any = None
_store: Any = None
_lock = asyncio.Lock()
_profiles_registered: bool = False

# Rastreia (tools_version, policy_version, skills_version) por usuário.
# Quando qualquer versão muda, o cache de LLM do usuário é invalidado.
_version_tracker: dict[str, tuple[int, int, int]] = {}


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
    """Abre (uma única vez) o checkpointer SQLite + store compartilhados.

    Todos os grafos (um por modelo) reusam estes recursos — assim há uma só
    conexão SQLite com o checkpointer, sem disputa de lock entre grafos.
    """
    global _checkpointer_ctx, _checkpointer, _store

    if _checkpointer is None:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        db_path = str(Path.home() / ".vectora" / "checkpoints.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(db_path)
        _checkpointer = await _checkpointer_ctx.__aenter__()

    if _store is None:
        from backend.services.backends import build_store

        _store = await build_store()


async def _build_graph_async(model_id: str = "") -> Any:
    """Compila um grafo deepagents para ``model_id`` (checkpointer/store compartilhados).

    Não muta estado global de cache — quem cacheia é ``get_user_agent``. Vazio
    em ``model_id`` usa o modelo padrão de env/settings.
    """
    await _ensure_infra()

    from typing import cast as _cast

    from deepagents import create_deep_agent
    from langchain_core.language_models.chat_models import BaseChatModel

    from backend.nodes.tools import ALL_TOOLS
    from backend.services.utils import load_llm

    # load_llm() retorna BaseChatModel concreto em runtime (deepagents exige
    # um BaseChatModel, não um modelo configurável). A anotação usa a base.
    llm: BaseChatModel = _cast("BaseChatModel", load_llm(model_id))
    subagents = _subagent_specs()  # sem user_id: toolset completo no singleton

    system_prompt = _build_session_system_prompt()

    global _profiles_registered
    if not _profiles_registered:
        from backend.services.profiles import _register_profiles

        _register_profiles()
        _profiles_registered = True

    # Middleware stack: HumanInTheLoopMiddleware com mode="ask" para o
    # singleton compartilhado. create_deep_agent já adiciona
    # SummarizationMiddleware ao stack base incondicionalmente.
    # E.B-5 (context_schema=VectoraContext) permitirá modo dinâmico por usuário.
    from backend.services.middleware import build_middleware_stack

    middleware = build_middleware_stack(permission_mode="ask")

    from backend.services.backends import build_backend_lazy
    from backend.services.skills import list_skill_paths
    from backend.vtypes.context import VectoraContext

    # Skills instaladas pelo usuário local (singleton compartilhado).
    # Paths absolutos — harness lê SKILL.md frontmatter on-demand.
    skill_paths = [str(p) for p in list_skill_paths("local")]

    # AGENTS.md paths para o MemoryMiddleware — injetado no system prompt.
    memory_paths = _agents_md_paths()

    compiled = create_deep_agent(
        llm,
        tools=ALL_TOOLS,
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
        "agent_factory: grafo compilado (model=%r, deepagents + %d tools + %d subagents + %d middleware)",
        model_id or "default",
        len(ALL_TOOLS),
        len(subagents),
        len(middleware),
    )
    return compiled


async def get_user_agent(user_id: str | None = None, model: str = "") -> Any:
    """Retorna o grafo compilado para ``model`` (cacheado por modelo).

    ``model`` é o ``"provider:model"`` escolhido no chat (vazio = padrão). Cada
    modelo tem seu grafo, construído sob demanda (uma vez) e cacheado; todos
    compartilham o mesmo checkpointer/store. Inicialização thread-safe via
    ``asyncio.Lock``. Registra a versão de tools/policy/skills do usuário.
    """
    key = model or "__default__"
    if key not in _graphs:
        async with _lock:
            if key not in _graphs:
                _graphs[key] = await _build_graph_async(model)

    if user_id:
        _track_versions(user_id)

    return _graphs[key]


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


async def aget_thread_messages(thread_id: str) -> list[tuple[str, str]]:
    """Mensagens persistidas de uma thread como ``(role, text)``.

    Lê o checkpoint do **mesmo** grafo que o chat escreve (deep-agent), o que
    é essencial: ``aget_state`` reconstrói os canais conforme o schema do grafo
    e a leitura por um grafo diferente devolve ``messages`` vazio. O laço
    abaixo desembrulha eventuais wrappers (``.bound``) até achar o
    ``CompiledStateGraph``, que é quem expõe ``aget_state``.

    Filtra mensagens de tool e turnos AI sem texto (só tool-call) — devolve um
    transcript humano/assistente limpo.
    """
    graph = await get_user_agent()
    compiled: Any = graph
    for _ in range(6):
        if hasattr(compiled, "aget_state"):
            break
        nxt = getattr(compiled, "bound", None)
        if nxt is None:
            break
        compiled = nxt
    if not hasattr(compiled, "aget_state"):
        return []

    config = {"configurable": {"thread_id": thread_id}}
    state = await compiled.aget_state(config)
    if not state or not state.values:
        return []

    out: list[tuple[str, str]] = []
    for msg in state.values.get("messages", []):
        msg_type = getattr(msg, "type", "")
        if msg_type == "tool":
            continue
        text = _message_text(getattr(msg, "content", "")).strip()
        if not text:
            continue
        role = "human" if msg_type == "human" else "assistant"
        out.append((role, text))
    return out


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
    """Remove entradas stale do cache de LLM bound (llm_tools._bound_cache)."""
    try:
        from backend.services import llm_tools

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
        from backend.services.backends import _resolve_workspace_root

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
    """Fecha o grafo + checkpointer SQLite. Idempotente.

    Deve ser chamado no shutdown do FastAPI (lifespan).
    """
    global _checkpointer_ctx, _checkpointer, _store

    async with _lock:
        if _checkpointer_ctx is None:
            return
        ctx = _checkpointer_ctx
        _checkpointer_ctx = None
        _checkpointer = None
        _store = None  # reaberto no próximo _ensure_infra
        _graphs.clear()
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
