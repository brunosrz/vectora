"""Filesystem tools: leitura, escrita, edição de arquivos, grep, listagem, terminal e artifacts."""

import asyncio
import json
import logging
import platform
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.services.ignore import is_ignored as _is_ignored
from backend.services.ignore import iter_files as _iter_files
from backend.services.ignore import load_ignore_spec as _load_ignore_spec
from backend.services.ignore import walk_files as _walk_files
from backend.services.security import (
    is_safe_regex_pattern,
    is_safe_shell_command,
    resolve_within_workspace,
)
from backend.services.terminal_stream import emit_terminal_line

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Q4 — Confinação ao workspace ativo (scope guard rails)
# ---------------------------------------------------------------------------


def _active_workspace(config: RunnableConfig | None) -> Any:
    """Resolve o Workspace ativo a partir do config (workspace_id)."""
    from backend.workspace.workspace import workspace_registry

    wid = None
    if config is not None:
        wid = (config.get("configurable") or {}).get("workspace_id")
    if wid:
        ws = workspace_registry.get(wid)
        if ws is not None:
            return ws
    return workspace_registry.get_or_create()


def _workspace_root(config: RunnableConfig | None) -> tuple[Path, Any]:
    """Retorna (root, workspace). Honra a worktree associada à thread, se houver."""
    ws = _active_workspace(config)
    worktree_path = None
    if config is not None:
        worktree_path = (config.get("configurable") or {}).get("worktree_path")
    root = Path(worktree_path) if worktree_path else Path(ws.cwd)
    return root, ws


def _confine(path: str, config: RunnableConfig | None) -> tuple[Path | None, str]:
    """Resolve ``path`` dentro do workspace ativo.

    Retorna (resolved_path, "") em sucesso ou (None, error_message) se o path
    escapar do workspace.
    """
    root, _ws = _workspace_root(config)
    resolved = resolve_within_workspace(path, root)
    if resolved is None:
        return None, (
            f"Error: Path '{path}' fora do workspace '{root}'. "
            "O Vectora só pode acessar arquivos dentro da pasta confiável."
        )
    return resolved, ""


def _require_trust(config: RunnableConfig | None) -> str:
    """Retorna mensagem de erro se o workspace ativo não for confiável, senão ""."""
    _, ws = _workspace_root(config)
    if not getattr(ws, "trusted", False):
        return (
            f"Error: Workspace '{ws.name}' não é confiável. Confirme a confiança "
            "na pasta antes de executar ações de escrita ou terminal."
        )
    return ""


def _require_local(config: RunnableConfig | None) -> str:
    """Rejeita workspaces remotos para tools de filesystem síncronas.

    Tools sync (`file_read`, `file_write`, `file_edit`, `grep`, `list`)
    fazem I/O direto via ``Path()`` e não passam pelo ``TransportBackend``
    async. Quando o workspace é SSH ou Codespace, retornamos uma mensagem
    clara — a próxima fase do G.2 vai expor essas operações via tools
    async dedicadas (``remote_read``, ``remote_write``).
    """
    _, ws = _workspace_root(config)
    transport = str(getattr(ws, "transport", "local"))
    if transport != "local":
        return (
            f"Error: Esta tool ainda só funciona em workspaces locais. "
            f"Workspace '{ws.name}' usa transport={transport!r}. "
            "Use a tool `terminal` para executar comandos remoto."
        )
    return ""


@tool(
    extras={
        "render_hint": "code_block",
        "category": "filesystem",
        "destructive": False,
        "icon": "file-text",
    }
)
def file_read(
    file_path: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lê conteúdo completo de um arquivo de texto.

    Args:
        file_path: Caminho relativo ou absoluto do arquivo

    Returns:
        Conteúdo do arquivo como string
    """
    if remote_err := _require_local(config):
        return remote_err
    resolved, err = _confine(file_path, config)
    if resolved is None:
        logger.warning("file_read blocked by scope check", extra={"path": file_path})
        return err

    try:
        content = resolved.read_text(encoding="utf-8")
        logger.info(
            "file_read completed", extra={"path": file_path, "size": len(content)}
        )
        return content
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except Exception:
        logger.exception("file_read failed", extra={"path": file_path})
        return "Error reading file. Check logs."


async def _run_hooks_and_autocommit_async(path: Path, root: Path, cfg: Any) -> None:
    """Roda hooks ``post_file_write`` + auto-commit opcional (``vectora.toml``)."""
    for cmd_template in cfg.hooks.post_file_write:
        cmd = cmd_template.replace("{file}", str(path))
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(root),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        logger.info(
            "post_file_write_hook_executed",
            extra={"command": cmd_template, "exit_code": proc.returncode},
        )

    if cfg.agent.auto_commit:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        add = await asyncio.create_subprocess_exec(
            "git",
            "add",
            str(path),
            cwd=str(root),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await add.wait()
        commit = await asyncio.create_subprocess_exec(
            "git",
            "commit",
            "-m",
            f"auto: update {rel}",
            cwd=str(root),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await commit.wait()
        logger.info("auto_commit_executed", extra={"path": str(rel)})


def _run_hooks_and_autocommit(path: Path, config: RunnableConfig | None) -> None:
    """Dispara hooks/auto-commit pós-escrita — nunca propaga falha pra tool.

    ``file_write``/``file_edit`` são tools síncronas (rodam via
    ``asyncio.to_thread`` no worker do LangGraph, sem event loop próprio
    nessa thread) — ``asyncio.run`` aqui abre um loop novo só pra essa
    chamada, isolado do loop principal do servidor.
    """
    try:
        from backend.workspace.workspace_config import load_workspace_config

        root, _ws = _workspace_root(config)
        cfg = load_workspace_config(root)
        if cfg is None or (not cfg.hooks.post_file_write and not cfg.agent.auto_commit):
            return
        asyncio.run(_run_hooks_and_autocommit_async(path, root, cfg))
    except Exception:
        logger.warning(
            "post_write_hooks_failed", extra={"path": str(path)}, exc_info=True
        )


@tool(
    extras={
        "render_hint": "diff",
        "category": "filesystem",
        "destructive": True,
        "icon": "file-edit",
        "invalidates": ["files", "diff"],
    }
)
def file_edit(
    file_path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Edita arquivo substituindo texto.

    Args:
        file_path: Caminho do arquivo
        old_text: Texto a encontrar (use "" para criar arquivo se não existir)
        new_text: Texto de substituição
        replace_all: Se True, substitui todas as ocorrências; padrão substitui apenas a 1ª

    Returns:
        Confirmação da edição
    """
    if remote_err := _require_local(config):
        return remote_err
    trust_err = _require_trust(config)
    if trust_err:
        return trust_err

    resolved, err = _confine(file_path, config)
    if resolved is None:
        logger.warning("file_edit blocked by scope check", extra={"path": file_path})
        return err

    try:
        path = resolved

        # Cria arquivo novo quando old_text="" e arquivo não existe
        if old_text == "" and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_text, encoding="utf-8")
            logger.info("file_edit created new file", extra={"path": file_path})
            _run_hooks_and_autocommit(path, config)
            return f"[OK] File created: {file_path}"

        content = path.read_text(encoding="utf-8")

        if old_text and old_text not in content:
            return "Error: Text not found in file"

        new_content = (
            content.replace(old_text, new_text)
            if replace_all
            else content.replace(old_text, new_text, 1)
        )
        path.write_text(new_content, encoding="utf-8")

        count = content.count(old_text) if replace_all else 1
        logger.info(
            "file_edit completed",
            extra={"path": file_path, "occurrences": count, "replace_all": replace_all},
        )
        _run_hooks_and_autocommit(path, config)
        return f"[OK] File edited successfully ({count} occurrence{'s' if count != 1 else ''} replaced)"
    except Exception:
        logger.exception("file_edit failed", extra={"path": file_path})
        return "Error editing file. Check logs."


@tool(
    extras={
        "render_hint": "code_block",
        "category": "filesystem",
        "destructive": True,
        "icon": "file-plus",
        "invalidates": ["files", "diff"],
    }
)
def file_write(
    file_path: str,
    content: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Cria ou sobrescreve completamente um arquivo com o conteúdo fornecido.

    Use para criar novos arquivos ou substituir o conteúdo completo de um existente.
    Para edições cirúrgicas (substituir trechos), prefira file_edit.

    Args:
        file_path: Caminho do arquivo (absoluto ou relativo)
        content: Conteúdo completo a escrever no arquivo

    Returns:
        Confirmação com caminho e tamanho em bytes
    """
    if remote_err := _require_local(config):
        return remote_err
    trust_err = _require_trust(config)
    if trust_err:
        return trust_err

    resolved, err = _confine(file_path, config)
    if resolved is None:
        logger.warning("file_write blocked by scope check", extra={"path": file_path})
        return err

    try:
        path = resolved
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        size = path.stat().st_size
        logger.info(
            "file_write completed", extra={"path": file_path, "size_bytes": size}
        )
        _run_hooks_and_autocommit(path, config)
        return f"[OK] File written: {file_path} ({size} bytes)"
    except Exception:
        logger.exception("file_write failed", extra={"path": file_path})
        return "Error writing file. Check logs."


@tool(
    extras={
        "render_hint": "table",
        "category": "filesystem",
        "destructive": False,
        "icon": "search",
    }
)
def grep(
    pattern: str,
    path: str = ".",
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Busca padrão em arquivos usando regex.

    Args:
        pattern: Padrão regex para buscar
        path: Caminho da pasta ou arquivo

    Returns:
        Linhas que correspondem ao padrão (arquivo:linha: conteúdo)
    """
    if remote_err := _require_local(config):
        return remote_err
    if not is_safe_regex_pattern(pattern):
        return "Error: Invalid or unsafe regex pattern"

    resolved, err = _confine(path, config)
    if resolved is None:
        return err

    try:
        results = []
        search_path = resolved
        base_dir = search_path if search_path.is_dir() else search_path.parent
        spec = _load_ignore_spec(base_dir)

        # iter_files poda node_modules/.venv/etc. durante o walk — rglob("*")
        # puro varria essas árvores inteiras antes de filtrar.
        files = (
            [search_path]
            if search_path.is_file()
            else _iter_files(search_path, "**/*", spec)
        )

        for file_path in files:
            if not file_path.is_file():
                continue
            if _is_ignored(file_path, base_dir, spec):
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_num, line in enumerate(content.split("\n"), 1):
                    if re.search(pattern, line):
                        results.append(f"{file_path}:{line_num}: {line}")
            except Exception:
                pass

        logger.info(
            "grep completed",
            extra={"pattern": pattern, "path": path, "matches": len(results)},
        )
        return "\n".join(results[:100]) if results else "No matches found"
    except Exception:
        logger.exception("grep failed", extra={"pattern": pattern, "path": path})
        return "Error during grep. Check logs."


@tool(
    extras={
        "render_hint": "table",
        "category": "filesystem",
        "destructive": False,
        "icon": "folder",
    }
)
def list_dir(
    path: str = ".",
    *,
    recursive: bool = False,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista arquivos em um diretório.

    Args:
        path: Caminho do diretório
        recursive: Se True, lista recursivamente

    Returns:
        Lista de arquivos e pastas com prefixo [DIR] ou [FILE]
    """
    if remote_err := _require_local(config):
        return remote_err
    resolved, err = _confine(path, config)
    if resolved is None:
        return err

    try:
        dir_path = resolved

        if not dir_path.exists():
            return f"Error: Directory '{path}' not found"
        if not dir_path.is_dir():
            return f"Error: '{path}' is not a directory"

        spec = _load_ignore_spec(dir_path)
        items = []
        if recursive:
            # walk_files poda node_modules/.venv/etc. durante o walk;
            # include_dirs=True mantém os diretórios não podados na listagem.
            entries, _ = _walk_files(dir_path, "**/*", spec, include_dirs=True)
            for item in entries:
                rel_path = item.relative_to(dir_path)
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {rel_path}")
        else:
            for item in sorted(dir_path.iterdir()):
                if _is_ignored(item, dir_path, spec):
                    continue
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {item.name}")

        logger.info(
            "list_dir completed",
            extra={"path": path, "recursive": recursive, "count": len(items)},
        )
        return "\n".join(items[:500]) if items else "(empty directory)"
    except Exception:
        logger.exception("list_dir failed", extra={"path": path})
        return "Error listing directory. Check logs."


#: Comandos em execução aguardando o próximo turno — chave é ``thread_id``.
#: Permite responder a um prompt interativo (ex.: "continuar? [y/N]") sem
#: matar o processo: a tool devolve o controle ao agente quando fica idle
#: por muito tempo com o processo ainda vivo, e uma chamada seguinte com
#: ``stdin_input`` retoma a MESMA sessão em vez de spawnar um comando novo.
_pending_terminal: dict[str, dict[str, Any]] = {}

_IDLE_TIMEOUT = 6.0
"""Sem output novo por esse tempo + processo vivo → provavelmente esperando
input; devolve o controle ao agente em vez de continuar bloqueado."""

_HARD_TIMEOUT = 60.0
"""Teto absoluto — depois disso o processo é morto de verdade."""


async def _drain_terminal_output(
    thread_id: str,
    proc: asyncio.subprocess.Process,
    output_lines: list[str],
    start: float,
    read_state: dict[str, Any] | None = None,
) -> str | None:
    """Aguarda output novo com idle-detection. None = processo terminou normalmente.

    Enquanto o processo está vivo, corre duas tasks de leitura (stdout/stderr)
    em paralelo com um watchdog que mede o tempo desde o último output. Se o
    processo ficar ``_IDLE_TIMEOUT`` segundos sem produzir nada (mas ainda
    vivo), assume que está esperando input — registra em ``_pending_terminal``
    (incluindo ``read_state``, para a próxima chamada REUSAR as mesmas tasks de
    leitura em vez de abrir um segundo leitor concorrente no mesmo stream) e
    devolve uma string com o output parcial + instrução.
    """
    if read_state is None:
        last_activity = [time.monotonic()]

        async def _stream(stream: asyncio.StreamReader | None) -> None:
            if stream is None:
                return
            while True:
                raw = await stream.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                output_lines.append(line)
                emit_terminal_line(line)
                last_activity[0] = time.monotonic()

        stdout_task = asyncio.ensure_future(_stream(proc.stdout))
        stderr_task = asyncio.ensure_future(_stream(proc.stderr))
        read_state = {
            "both": asyncio.gather(stdout_task, stderr_task),
            "last_activity": last_activity,
        }

    both = read_state["both"]
    last_activity = read_state["last_activity"]

    while True:
        try:
            await asyncio.wait_for(asyncio.shield(both), timeout=0.3)
            break  # ambos os streams fecharam — processo terminou de escrever
        except TimeoutError:
            pass

        if time.monotonic() - start > _HARD_TIMEOUT:
            both.cancel()
            proc.kill()
            await proc.wait()
            _pending_terminal.pop(thread_id, None)
            logger.warning("terminal_command_timeout", extra={"thread_id": thread_id})
            return "Error: Command timed out after 60 seconds"

        if (
            proc.returncode is None
            and time.monotonic() - last_activity[0] > _IDLE_TIMEOUT
        ):
            if thread_id:
                _pending_terminal[thread_id] = {
                    "proc": proc,
                    "output_lines": output_lines,
                    "read_state": read_state,
                }
            return "\n".join(output_lines) + (
                "\n\n[Comando ainda rodando, sem output novo há alguns "
                "segundos — pode estar esperando input. Use "
                'terminal(stdin_input="...") para responder no mesmo '
                'processo, ou stdin_input="\\x03" para tentar Ctrl+C.]'
            )

    await proc.wait()
    return None


@tool(
    extras={
        "render_hint": "terminal_output",
        "category": "filesystem",
        "destructive": True,
        "icon": "terminal",
        "invalidates": ["files", "diff"],
    }
)
async def terminal(
    command: str = "",
    stdin_input: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Executa um comando shell de forma assíncrona (não bloqueia o event loop).

    Suporta comandos interativos: se um comando anterior nesta mesma thread
    ainda estiver rodando esperando input (ex.: prompt "continuar? [y/N]"),
    chame de novo passando só ``stdin_input`` (sem ``command``) para
    responder no MESMO processo, em vez de spawnar um comando novo.

    Args:
        command: Comando shell para executar. Vazio quando só respondendo
            a um prompt pendente via ``stdin_input``.
        stdin_input: Texto para escrever no stdin de um comando pendente
            desta thread (envia com quebra de linha automática). Requer que
            exista um comando ainda rodando e esperando input.

    Returns:
        Saída do comando (stdout + stderr) ou mensagem de erro se bloqueado
    """
    trust_err = _require_trust(config)
    if trust_err:
        return trust_err

    thread_id = (
        str((config.get("configurable") or {}).get("thread_id", "")) if config else ""
    )
    pending = _pending_terminal.get(thread_id) if thread_id else None

    if stdin_input is not None:
        if pending is None or pending["proc"].returncode is not None:
            return (
                "Error: não há comando pendente esperando input nesta sessão "
                "— chame `terminal` com um `command` novo."
            )
        proc = pending["proc"]
        output_lines = pending["output_lines"]
        if proc.stdin is None:
            _pending_terminal.pop(thread_id, None)
            return "Error: stdin do processo pendente não está disponível."
        try:
            proc.stdin.write((stdin_input + "\n").encode("utf-8"))
            await proc.stdin.drain()
        except Exception:
            _pending_terminal.pop(thread_id, None)
            return "Error: falha ao enviar input — o processo pode ter encerrado."

        start = time.monotonic()
        idle_result = await _drain_terminal_output(
            thread_id, proc, output_lines, start, read_state=pending.get("read_state")
        )
        if idle_result is not None:
            return idle_result
        _pending_terminal.pop(thread_id, None)
        output = "\n".join(output_lines)
        return output or f"Command executed with exit code {proc.returncode}"

    if not command:
        return "Error: informe `command` (ou `stdin_input` para responder a um comando pendente)."

    # Normaliza comandos Unix → Windows quando necessário
    if platform.system() == "Windows":
        command = re.sub(r"\bmkdir\s+-p\s+", "mkdir ", command)
        command = re.sub(r"\bmkdir\s+-p\s*$", "mkdir .", command)

    if not is_safe_shell_command(command):
        logger.warning(
            "terminal command blocked by safety check",
            extra={"command": command[:50]},
        )
        return (
            f"Error: Command '{command}' is blocked for safety. "
            "Destructive commands like rm -rf, mkfs, dd if=/dev/zero, "
            "and fork bombs are not permitted."
        )

    root, _ws = _workspace_root(config)

    # G.2.3 — Workspace remoto (SSH ou Codespace): delega via transport.
    # O streaming linha-a-linha e o stdin interativo não são suportados
    # nesse caminho ainda; o output volta inteiro depois que o comando termina.
    transport = str(getattr(_ws, "transport", "local"))
    if transport != "local":
        from backend.transport import get_transport

        backend = get_transport(_ws)
        cwd_remote = getattr(_ws, "remote_path", None) or str(root)
        result = await backend.run(
            ["sh", "-c", command],
            cwd=cwd_remote,
            timeout=30.0,
        )
        output = (result.stdout + result.stderr).strip()
        logger.info(
            "terminal_command_remote",
            extra={
                "command": command[:50],
                "exit_code": result.exit_code,
                "transport": transport,
            },
        )
        return output or f"Command executed with exit code {result.exit_code}"

    try:
        # asyncio.create_subprocess_shell não bloqueia o event loop
        # permitindo que o UI (Rich panels) e outras tarefas continuem rodando.
        # cwd confina o comando ao workspace ativo (Q4 — scope guard rails).
        # stdin=PIPE viabiliza responder a prompts interativos (stdin_input).
        proc = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(root),
        )

        output_lines: list[str] = []
        start = time.monotonic()
        idle_result = await _drain_terminal_output(thread_id, proc, output_lines, start)
        if idle_result is not None:
            return idle_result

        output = "\n".join(output_lines)

        logger.info(
            "terminal_command_executed",
            extra={
                "command": command[:50],
                "exit_code": proc.returncode,
                "output_length": len(output),
            },
        )

        return output or f"Command executed with exit code {proc.returncode}"

    except Exception:
        logger.exception("terminal_command_failed", extra={"command": command[:50]})
        if thread_id:
            _pending_terminal.pop(thread_id, None)
        if proc is not None and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
        return "Error executing command. Check logs."


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------

_VALID_ARTIFACT_TYPES = {
    "plan",
    "spec",
    "task_list",
    "overview",
    "guide",
    "architecture",
    "implementation",
}


def _artifact_slug(title: str) -> str:
    """Converte título em slug kebab-case para nome de arquivo (max 50 chars)."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:50] or "artifact"


# Slugs genéricos demais por tipo — título como "Plano" vira "plano.md", sem
# dizer do que trata. Força o modelo a escolher um título específico (ex:
# "Plano de Implementação do Jogo da Cobrinha em Godot 4.7").
_GENERIC_TITLE_SLUGS: dict[str, set[str]] = {
    "plan": {"plan", "plano", "planejamento", "plano-de-implementacao"},
    "spec": {"spec", "especificacao", "especificacoes", "especificacao-tecnica"},
    "task_list": {
        "tasks",
        "task-list",
        "tarefas",
        "todo",
        "todos",
        "lista-de-tarefas",
    },
    "overview": {"overview", "visao-geral", "resumo", "resumo-executivo"},
    "guide": {"guide", "guia", "tutorial"},
    "architecture": {"architecture", "arquitetura"},
    "implementation": {"implementation", "implementacao"},
}


def _rotate_artifact_history(artifact_dir: Path, slug: str, content: str) -> Path:
    """Grava ``content`` como a versão ATUAL (``{slug}.md``), preservando a
    versão anterior (se houver) como histórico imutável numerado.

    O arquivo sem sufixo é sempre a versão mais recente — a UI (Plan tab)
    consulta por ele diretamente. Antes de sobrescrever, a versão atual vira
    ``{slug}-N.md`` (N = próximo número livre), então o histórico cresce em
    ordem cronológica sem nunca perder uma versão anterior.
    """
    current = artifact_dir / f"{slug}.md"
    if current.exists():
        n = 1
        while (artifact_dir / f"{slug}-{n}.md").exists():
            n += 1
        current.rename(artifact_dir / f"{slug}-{n}.md")
    current.write_text(content, encoding="utf-8")
    return current


def _mirror_artifact_to_workspace(
    config: RunnableConfig | None, artifact_type: str, slug: str, content: str
) -> None:
    """Espelha a versão atual do artifact dentro do workspace ativo
    (``<workspace_root>/.vectora/{type}s/{slug}.md``) — sempre a última
    versão, sem histórico (o histórico imutável vive só em
    ``~/.vectora/artifacts/``). Só espelha quando a sessão tem um
    ``workspace_id`` explícito no config — sem isso, não força a criação de
    um workspace default só pra gravar o espelho. Best-effort: falha aqui
    nunca derruba a criação do artifact.
    """
    workspace_id = (
        (config.get("configurable") or {}).get("workspace_id") if config else None
    )
    if not workspace_id:
        return
    try:
        root, _ws = _workspace_root(config)
        mirror_dir = root / ".vectora" / f"{artifact_type}s"
        mirror_dir.mkdir(parents=True, exist_ok=True)
        (mirror_dir / f"{slug}.md").write_text(content, encoding="utf-8")
    except Exception:
        logger.exception("create_artifact: falha ao espelhar '%s' no workspace", slug)


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


def _thread_id(config: RunnableConfig | None) -> str:
    """Extrai o thread_id real do RunnableConfig injetado pelo LangGraph.

    Nunca confiar no modelo pra "lembrar" de passar o ID certo — o system
    prompt é montado por workspace (cacheado), não por thread, então o
    thread_id real nunca aparece literalmente no texto do prompt. Ler do
    config elimina a classe inteira de erro "salvou no artifact errado".
    """
    return (
        str((config.get("configurable") or {}).get("thread_id", "")) if config else ""
    )


@tool(
    extras={
        "render_hint": "artifact",
        "category": "artifacts",
        "destructive": False,
        "icon": "file-code",
    }
)
def create_artifact(
    artifact_type: str,
    title: str,
    content: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Cria e persiste um artifact estruturado em ~/.vectora/artifacts/{session_id}/{slug}.md.

    Use esta tool quando o usuário pedir um documento que deve ser salvo permanentemente:
    plano de implementação, especificação técnica, lista de tarefas, visão geral de
    projeto, guia/tutorial, diagrama de arquitetura ou implementação de referência.
    NÃO use para respostas conversacionais — apenas para documentos que o usuário
    vai querer consultar depois.

    Versionamento: {slug}.md é sempre a versão MAIS RECENTE; ao salvar de novo com
    o mesmo título, a versão anterior vira histórico imutável ({slug}-1.md,
    {slug}-2.md, ...). Se a sessão tem um workspace ativo, a versão atual também é
    espelhada em <workspace>/.vectora/{artifact_type}s/{slug}.md (sem histórico —
    só a última versão, visível direto no projeto).

    Args:
        artifact_type: Tipo do artifact. Valores válidos:
            - "plan"           → plano de implementação, roadmap
            - "spec"           → especificação técnica, requisitos
            - "task_list"      → lista de tarefas, TODOs
            - "overview"       → visão geral de projeto, resumo executivo
            - "guide"          → guia, tutorial, how-to
            - "architecture"   → decisões de arquitetura, diagramas
            - "implementation" → código de referência, snippets documentados
        title: Título ESPECÍFICO e descritivo do artifact (ex: "Plano de
            Implementação do Jogo da Cobrinha em Godot 4.7"). Nunca use só o nome
            do tipo ("Plano", "Spec", "Tarefas") — isso é rejeitado com erro;
            o título vira o nome do arquivo e precisa dizer do que o documento trata.
        content: Conteúdo completo em markdown

    Returns:
        JSON com path, title, artifact_type, session_id e created_at
    """
    if artifact_type not in _VALID_ARTIFACT_TYPES:
        return json.dumps(
            {
                "error": f"artifact_type inválido: '{artifact_type}'. "
                f"Valores válidos: {sorted(_VALID_ARTIFACT_TYPES)}"
            }
        )

    if not title or not title.strip():
        return json.dumps({"error": "title não pode ser vazio"})

    if not content or not content.strip():
        return json.dumps({"error": "content não pode ser vazio"})

    session_id = _thread_id(config)
    if not session_id:
        return json.dumps(
            {"error": "Sessão não identificada — não foi possível salvar o artifact."}
        )

    slug = _artifact_slug(title.strip())
    if slug in _GENERIC_TITLE_SLUGS.get(artifact_type, set()):
        return json.dumps(
            {
                "error": (
                    f"title '{title.strip()}' é genérico demais — descreva do "
                    "que o artifact trata (ex.: 'Plano de Implementação do "
                    "Jogo da Cobrinha em Godot 4.7', não apenas 'Plano')."
                )
            }
        )

    artifact_dir = Path.home() / ".vectora" / "artifacts" / session_id

    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        stripped_content = content.strip()
        path = _rotate_artifact_history(artifact_dir, slug, stripped_content)
        _mirror_artifact_to_workspace(config, artifact_type, slug, stripped_content)

        created_at = datetime.now(UTC).isoformat()
        logger.info(
            "create_artifact: salvo '%s' (%s) → %s",
            title,
            artifact_type,
            path,
        )

        return json.dumps(
            {
                "path": str(path),
                "title": title.strip(),
                "artifact_type": artifact_type,
                "session_id": session_id,
                "created_at": created_at,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        logger.exception("create_artifact: falha ao salvar '%s'", title)
        return json.dumps({"error": f"Falha ao salvar artifact: {e}"})
