"""Coder Worker — LLM especializado em operações de código e filesystem.

Recebe ALL_TOOLS — a especialidade vem do system prompt, não de restrição de ferramentas.
Objetivo: criar/editar arquivos, executar comandos, navegação de código.
Também capaz de indexar pastas via ingest_docs quando solicitado.

``SUBAGENT_SPEC`` é o dict canônico consumido por ``agent_factory._subagent_specs()``.
Exportado para que o factory não precise duplicar descrição/ferramentas.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage

from src.agents._identity import VECTORA_IDENTITY
from src.nodes.base import invoke_llm
from src.nodes.tools import FS_TOOLS, GIT_TOOLS, MEMORY_TOOLS, RAG_TOOLS
from src.services.llm_tools import get_user_bound_llm, user_id_from_config
from src.services.utils import load_llm
from src.types import CoderResult

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable, RunnableConfig

    from src.state import State

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""{VECTORA_IDENTITY}

---

## Seu Papel — Coder Agent

Você é o **Coder Agent** do Vectora. Especializado em desenvolvimento de software e
operações de filesystem. Tem acesso a **todas as ferramentas** do Vectora.

### Ferramentas — por prioridade de uso

#### 🗂️ Filesystem (prioridade principal)
- `file_read`, `file_edit`, `file_write` — ler, editar e criar arquivos
- `grep` — busca em código por padrões/regex
- `list_dir` — listar diretórios
- `terminal` — executar comandos shell (git, npm, pip, uv, docker, pytest...)

#### 📚 RAG e Indexação (use quando solicitado)
- `ingest_docs` — **indexa uma PASTA INTEIRA no LanceDB** (batch)
  - Uso: quando o usuário pedir "faça embedding da pasta X", "indexa o projeto", "rag add"
  - Parâmetros: `directory_path`, `collection` (default: "articles"), `glob_pattern` (default: "**/*.py")
  - **NUNCA** use `terminal` para chamar `/rag` — `ingest_docs` é a ferramenta correta
- `embedding` — enfileira um único documento de texto para indexação
- `vector_search` — busca semântica na base indexada

#### 🌐 Busca web (quando precisar de informação externa)
- `web_search` — busca web em tempo real
- `fetch_url` — extrai conteúdo de uma URL específica

#### 🧠 Memória
- `save_memory`, `get_memory`, `delete_memory` — contexto persistente entre sessões

### Git e terminal são livres
Execute qualquer subcomando git (`git status`, `git add`, `git commit`, `git push`,
`git log`, `git diff`...) **sem pedir confirmação ao usuário**. Git é essencial para
desenvolvimento. Apenas `rm -rf`, `mkfs` e equivalentes destrutivos são bloqueados
automaticamente pela tool.

### Proatividade
- Ao criar ou editar código, execute testes automaticamente se existirem
- Use `grep` para navegar no código antes de editar
- Prefira edições cirúrgicas (`file_edit`) a reescritas completas (`file_write`)

### Estilo
- Mostre o código gerado ou editado no resultado
- Explique brevemente o que foi feito e por quê
- Adapte o idioma ao da conversa
"""

#: Spec canônica do subagent coder para ``create_deep_agent``.
#: Importada por ``agent_factory._subagent_specs(user_id)`` que filtra
#: as tools de acordo com a política ABAC antes de passar ao grafo.
SUBAGENT_SPEC: dict[str, Any] = {
    "name": "coder",
    "description": (
        "Especialista em filesystem, código, terminal e git. "
        "Use para: criar/editar/ler arquivos, executar comandos, "
        "git (commit/branch/push), npm/pip/uv, testes, "
        "indexar/embedar pastas (ingest_docs)."
    ),
    "system_prompt": SYSTEM_PROMPT,
    "tools": FS_TOOLS + GIT_TOOLS + MEMORY_TOOLS + RAG_TOOLS,
}

_coder_llm = None


def _get_coder_llm() -> Runnable:  # mantido p/ Studio/local; o nó usa bind por user
    global _coder_llm
    if _coder_llm is None:
        tools = SUBAGENT_SPEC["tools"]
        if not tools:
            _coder_llm = load_llm()
            logger.warning("coder_worker: sem ferramentas disponíveis")
        else:
            _coder_llm = load_llm().bind_tools(tools)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            logger.debug("coder_worker LLM inicializado com %d tools", len(tools))
    return _coder_llm


# ---------------------------------------------------------------------------
# Nós do grafo
# ---------------------------------------------------------------------------


async def coder_finalize(state: State) -> dict:
    """Extrai resultado estruturado da sessão do coder e prepara para síntese.

    Roda após o coder concluir (sem mais tool_calls). Analisa o histórico de
    mensagens heuristicamente para produzir um CoderResult sem custo de LLM:
    - `files_changed` → coletado das tool_calls file_write/file_edit
    - `tests_run`     → detectado em chamadas terminal com pytest/test
    - `summary`       → último AIMessage do coder sem tool_calls
    - `success`       → True por padrão; False se a última mensagem indica erro

    O resultado fica em `state["coder_result"]` para o orchestrator sintetizar.
    """
    messages = list(state.get("messages", []))

    files_changed: list[str] = []
    tests_run = False
    _file_ops = frozenset(
        {"file_write", "file_write_tool", "file_edit", "file_edit_tool"}
    )
    _test_keywords = ("pytest", "npm test", "cargo test", "go test", "rspec", "jest")

    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            name = tc.get("name", "") if isinstance(tc, dict) else ""
            args = tc.get("args", {}) if isinstance(tc, dict) else {}
            if name in _file_ops:
                path = str(args.get("path") or args.get("file_path", "")).strip()
                if path and path not in files_changed:
                    files_changed.append(path)
            elif name in ("terminal", "terminal_tool"):
                cmd = str(args.get("command", "")).lower()
                if any(kw in cmd for kw in _test_keywords):
                    tests_run = True

    # Resumo = último AIMessage do coder sem tool_calls
    summary = ""
    success = True
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            c = msg.content
            summary = c if isinstance(c, str) else str(c)
            # Heurística simples: se começa com "Erro" ou "Error" → falha
            if summary.lower().startswith(("erro", "error", "falha", "failed")):
                success = False
            break

    result = CoderResult(
        summary=summary or "Tarefa concluída.",
        files_changed=files_changed,
        tests_run=tests_run,
        success=success,
        next_steps=None,
    )

    logger.info(
        "coder_finalize: %d arquivos, testes=%s, sucesso=%s",
        len(files_changed),
        tests_run,
        success,
    )
    return {"coder_result": result}


async def coder(state: State, config: RunnableConfig = None) -> dict:  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
    """Agent de código: cria/edita arquivos, executa terminal e git.

    Especializado em tarefas de desenvolvimento:
    - Ler e editar código-fonte
    - Executar comandos (git, npm, pip, terminal)
    - Criar estrutura de projeto
    - Grep e navegação em arquivos

    O LLM é bindado ao toolset do usuário (built-ins permitidas + MCP) a partir
    do user_id do config. Quando recebe orchestrator_task, injeta a instrução no
    topo do system prompt.
    """
    task = state.get("orchestrator_task")
    task_block = f"\n\n## Task delegada pelo Orchestrator\n{task}" if task else ""

    logger.info("coder: processando mensagem%s", " (task delegada)" if task else "")
    llm = await get_user_bound_llm(user_id_from_config(config))
    return await invoke_llm(llm, state, system_prompt=SYSTEM_PROMPT + task_block)
