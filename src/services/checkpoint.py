"""LangGraph Checkpoint Management for Conversation State Persistence.

Manages SQLite-backed checkpointing for LangGraph execution state.
Enables resuming interrupted conversations, thread-level history,
and state snapshots for debugging and auditing.

Também expõe a estratégia git de "checkpoint de workspace" usada pelo rewind
(``create_git_checkpoint``/``restore_git_checkpoint``/``list_git_checkpoints``):
snapshots do worktree gravados como commits soltos em
``refs/vectora/checkpoints/<thread_id>``, sem mover HEAD nem o índice real."""

import logging
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import git
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def Checkpointer(
    db_dsn: str | None = None,
) -> AsyncGenerator[AsyncSqliteSaver]:
    """Constrói checkpointer SQLite assíncrono para persistência local de conversas.

    Usa aiosqlite via AsyncSqliteSaver do LangGraph. O arquivo SQLite é criado
    automaticamente no diretório `data/` na raiz do projeto.

    **Concorrência:** WAL mode habilitado automaticamente para permitir
    leituras simultâneas enquanto o BackgroundWorker escreve embeddings.

    Args:
        db_dsn: Caminho para o arquivo SQLite. Se None, usa o padrão de `settings.db_dsn`.
    """
    conn_string = db_dsn or settings.db_dsn
    if conn_string is None:
        msg = "db_dsn not configured"
        raise RuntimeError(msg)
    async with AsyncSqliteSaver.from_conn_string(conn_string) as checkpointer:
        # Enable WAL mode for concurrent reads + writes
        # Critical: Chat reads/writes messages while BackgroundWorker accesses queue
        try:
            await checkpointer.conn.execute("PRAGMA journal_mode=WAL;")
            await checkpointer.conn.execute("PRAGMA synchronous=NORMAL;")
            logger.info("Checkpointer: WAL mode enabled for concurrent access")
        except Exception as e:
            logger.warning("Could not enable WAL mode", extra={"error": str(e)})

        yield checkpointer


# ---------------------------------------------------------------------------
# Estratégia git de checkpoint de workspace (rewind — A.2)
# ---------------------------------------------------------------------------

# Autor fixo dos commits de checkpoint — nunca aparecem como autoria do
# usuário em `git log`/`git blame` da branch de trabalho (ficam isolados em
# `refs/vectora/checkpoints/*`, fora de `git branch -a`).
_CHECKPOINT_AUTHOR_NAME = "Vectora"
_CHECKPOINT_AUTHOR_EMAIL = "vectora@local"
_CHECKPOINT_REF_PREFIX = "refs/vectora/checkpoints/"


def checkpoint_ref(thread_id: str) -> str:
    """Nome da ref que encadeia os checkpoints de uma thread."""
    return f"{_CHECKPOINT_REF_PREFIX}{thread_id}"


def _checkpoint_env(index_file: str) -> dict[str, str]:
    return {
        "GIT_INDEX_FILE": index_file,
        "GIT_AUTHOR_NAME": _CHECKPOINT_AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": _CHECKPOINT_AUTHOR_EMAIL,
        "GIT_COMMITTER_NAME": _CHECKPOINT_AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": _CHECKPOINT_AUTHOR_EMAIL,
    }


def create_git_checkpoint(
    repo: git.Repo, thread_id: str, message: str
) -> dict[str, Any]:
    """Cria um commit-snapshot do worktree atual, sem tocar HEAD/índice/branch.

    Usa um índice git temporário (``GIT_INDEX_FILE`` apontando para um arquivo
    descartável): semeia-o a partir da árvore do HEAD via ``read-tree`` e roda
    ``add -A`` contra ele — captura staged + unstaged + untracked num único
    ``write-tree``, exatamente como ``git stash --include-untracked`` faz
    internamente, mas sem alterar `.git/index` nem o worktree do usuário.

    O commit resultante encadeia ao checkpoint anterior da thread (via
    ``refs/vectora/checkpoints/<thread_id>``) ou a HEAD, no primeiro
    checkpoint — formando um histórico linear navegável por
    ``git log refs/vectora/checkpoints/<thread_id>`` sem poluir
    ``git branch -a``.

    Retorna ``{"status": "ok", "sha": <commit>, "tree": <tree>}`` ou
    ``{"status": "error", "message": ...}`` em caso de falha do git.
    """
    try:
        head_sha: str | None = repo.head.commit.hexsha
    except (ValueError, git.GitCommandError):
        head_sha = None

    ref = checkpoint_ref(thread_id)
    try:
        parent_sha = repo.git.rev_parse(ref).strip()
    except git.GitCommandError:
        parent_sha = head_sha

    try:
        with tempfile.TemporaryDirectory(prefix="vectora-checkpoint-") as tmp_dir:
            index_file = str(Path(tmp_dir) / "index")
            env = _checkpoint_env(index_file)
            if head_sha is not None:
                repo.git.read_tree(head_sha, env=env)
            repo.git.add("-A", env=env)
            tree_sha = repo.git.write_tree(env=env).strip()

            commit_args: list[str] = [tree_sha]
            if parent_sha is not None:
                commit_args += ["-p", parent_sha]
            commit_args += ["-m", message]
            commit_sha = repo.git.commit_tree(*commit_args, env=env).strip()

            repo.git.update_ref(ref, commit_sha)
    except git.GitCommandError as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "sha": commit_sha, "tree": tree_sha}


def restore_git_checkpoint(repo: git.Repo, sha: str) -> dict[str, Any]:
    """Restaura o worktree (e o índice) para o estado gravado em ``sha``.

    Equivalente a ``git restore --source=<sha> --worktree --staged -- .`` —
    sobrescreve arquivos rastreados e staged pelo conteúdo do snapshot, mas
    **não** remove arquivos criados depois do checkpoint (limitação conhecida
    de `git restore`; cobertura completa de "desfazer criação de arquivo"
    fica para A.3 — snapshot diferencial).
    """
    try:
        repo.git.restore("--source", sha, "--worktree", "--staged", "--", ".")
    except git.GitCommandError as exc:
        return {"status": "error", "message": str(exc)}
    return {"status": "ok", "sha": sha}


def list_git_checkpoints(repo: git.Repo, thread_id: str, n: int = 50) -> dict[str, Any]:
    """Lista os checkpoints da thread, do mais recente ao mais antigo."""
    ref = checkpoint_ref(thread_id)
    try:
        commits = list(repo.iter_commits(ref, max_count=n))
    except git.GitCommandError:
        return {"status": "ok", "checkpoints": []}

    return {
        "status": "ok",
        "checkpoints": [
            {
                "sha": c.hexsha,
                "message": c.message.strip(),
                "date": c.authored_datetime.isoformat(),
            }
            for c in commits
        ],
    }
